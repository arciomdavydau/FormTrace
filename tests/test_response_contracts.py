"""Exercise published output schemas through the actual MCP client."""

from __future__ import annotations

import json
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic import ValidationError

from fitness_hub.clients.hevy import HevyClient
from fitness_hub.config import Settings
from fitness_hub.models.responses import SnapshotSource, TrainingSummary
from fitness_hub.server import create_server
from fitness_hub.services.training import TrainingService
from tests.fakes import FakeTrainingSource
from tests.helpers import assert_output_matches_schema


@pytest.fixture
def local_hevy_server(
    sample_hevy_workouts_payload: dict[str, Any],
    sample_hevy_exercise_templates_payload: dict[str, Any],
) -> Iterator[tuple[str, list[str]]]:
    """Serve fixed responses to the separate stdio subprocess, without contacting Hevy."""
    paths: list[str] = []
    responses = {
        "/v1/workouts": sample_hevy_workouts_payload,
        "/v1/exercise_templates": sample_hevy_exercise_templates_payload,
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            paths.append(path)
            if self.headers.get("api-key") != "fictional-test-key":
                self.send_error(401)
                return
            if path not in responses:
                self.send_error(404)
                return
            payload = json.dumps(responses[path]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", paths
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_response_contract_rejects_coerced_or_unexpected_source_fields() -> None:
    with pytest.raises(ValidationError):
        SnapshotSource.model_validate(
            {
                "provider": "fixture",
                "fetched_at": "2026-11-09T00:00:00Z",
                "complete": "yes",
                "cache_ttl_seconds": 300,
            }
        )
    with pytest.raises(ValidationError):
        SnapshotSource.model_validate(
            {
                "provider": "fixture",
                "fetched_at": "2026-11-09T00:00:00Z",
                "complete": True,
                "cache_ttl_seconds": 300,
                "unexpected": True,
            }
        )


@pytest.mark.asyncio
async def test_response_contract_rejects_inconsistent_workout_counts() -> None:
    report = await TrainingService(FakeTrainingSource(), provider="fixture").report(
        "2026-11-02", "2026-11-08", "UTC"
    )
    summary = report["current"]
    summary["working_sets"] += 1
    with pytest.raises(ValidationError, match="working_sets"):
        TrainingSummary.model_validate(summary)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "arguments", "expected_keys"),
    [
        (
            "get_training_report",
            {"start_date": "2026-11-02", "end_date": "2026-11-08"},
            {"period", "previous_period", "source", "current", "previous", "warnings"},
        ),
        (
            "search_exercises",
            {"query": "bench"},
            {"source", "total_matches", "truncated", "exercises"},
        ),
        (
            "get_exercise_progression",
            {"exercise_id": "fixture-bench", "start_date": "2026-11-02", "end_date": "2026-11-08"},
            {"exercise_id", "period", "source", "sessions", "note"},
        ),
        ("get_workout_details", {"workout_id": "fixture-workout-1"}, {"source", "workout"}),
    ],
)
async def test_analytics_tools_expose_valid_unwrapped_output_contracts(
    name: str, arguments: dict[str, Any], expected_keys: set[str]
) -> None:
    server = create_server(TrainingService(FakeTrainingSource(), provider="fixture"))
    async with Client(server) as client:
        result = await client.call_tool(name, arguments)
        assert result.structured_content is not None
        assert set(result.structured_content) == expected_keys
        await assert_output_matches_schema(client, name, result.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_hevy_read_envelope_preserves_provider_fields_not_known_to_hub() -> None:
    respx.get("https://api.hevyapp.com/v1/user/info").mock(
        return_value=httpx.Response(200, json={"data": {"future_field": {"version": 2}}})
    )
    settings = Settings(_env_file=None, hevy_api_key="fictional-test-key")
    server = create_server(TrainingService(HevyClient(settings)))
    async with Client(server) as client:
        result = await client.call_tool("get_hevy_profile", {})
        assert result.structured_content is not None
        assert result.structured_content["data"]["data"]["future_field"] == {"version": 2}
        await assert_output_matches_schema(client, "get_hevy_profile", result.structured_content)


@pytest.mark.asyncio
async def test_real_stdio_server_uses_mocked_hevy_in_an_isolated_directory(
    tmp_path: Path, local_hevy_server: tuple[str, list[str]]
) -> None:
    base_url, paths = local_hevy_server
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "fitness_hub.server"],
        cwd=str(tmp_path),
        env={
            "HEVY_API_BASE_URL": base_url,
            "HEVY_API_KEY": "fictional-test-key",
            "NO_PROXY": "127.0.0.1,localhost",
        },
    )
    async with Client(transport) as client:
        result = await client.call_tool(
            "get_training_report",
            {
                "start_date": "2026-11-02",
                "end_date": "2026-11-08",
                "timezone": "UTC",
            },
        )
        assert result.structured_content is not None
        assert result.structured_content["source"]["provider"] == "hevy"
        assert result.structured_content["current"]["working_sets"] == 5
        await assert_output_matches_schema(client, "get_training_report", result.structured_content)
    assert paths == ["/v1/workouts", "/v1/exercise_templates"]
