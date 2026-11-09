"""Behavioral checks for summaries, source completeness and the MCP interface."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from fastmcp import Client

from fitness_hub.clients.base import UpstreamAPIError
from fitness_hub.clients.hevy import HevyClient
from fitness_hub.config import Settings
from fitness_hub.demo import DemoHevyClient
from fitness_hub.models.workouts import ExerciseLog, ExerciseSet, SetType, WorkoutSession
from fitness_hub.server import create_server
from fitness_hub.services.training import TrainingService


@pytest.mark.asyncio
async def test_report_counts_primary_and_secondary_without_merging_them() -> None:
    service = TrainingService(DemoHevyClient(), provider="demo")
    report = await service.report("2026-11-02", "2026-11-08", "Europe/Warsaw")
    current = report["current"]
    assert report["source"]["provider"] == "demo"
    assert report["previous_period"] == {"start": "2026-10-26", "end": "2026-11-01"}
    assert current["workouts_count"] == 2
    assert current["working_sets"] == 6
    assert current["warmup_sets"] == 1
    assert current["muscle_groups"]["primary_working_sets"] == {"chest": 4, "quadriceps": 2}
    assert current["muscle_groups"]["secondary_involvement_sets"]["triceps"] == 4
    assert report["previous"]["workouts_count"] == 0


@pytest.mark.asyncio
async def test_unknown_set_types_and_templates_are_not_counted_as_known_work() -> None:
    class Source(DemoHevyClient):
        async def get_all_workouts(self) -> list[WorkoutSession]:
            return [
                WorkoutSession(
                    id="1",
                    title="test",
                    start_time="2026-10-24T22:30:00Z",
                    exercises=[
                        ExerciseLog(
                            title="custom",
                            exercise_template_id="missing",
                            sets=[
                                ExerciseSet(set_type=SetType.UNKNOWN, reps=5),
                                ExerciseSet(set_type=SetType.NORMAL, reps=5),
                            ],
                        )
                    ],
                )
            ]

    report = await TrainingService(Source(), provider="test").report(
        "2026-10-25", "2026-10-25", "Europe/Warsaw"
    )
    assert report["current"]["workouts_count"] == 1  # local date across DST change
    assert report["current"]["working_sets"] == 1
    assert report["current"]["unknown_type_sets"] == 1
    assert report["current"]["muscle_groups"]["unclassified_working_sets"] == 1


@pytest.mark.asyncio
async def test_progression_retains_weight_repetitions_and_missing_rpe() -> None:
    service = TrainingService(DemoHevyClient(), provider="demo")
    result = await service.progression("demo-bench", "2026-11-02", "2026-11-08", "UTC")
    assert len(result["sessions"]) == 2
    assert result["sessions"][0]["working_sets"][0] == {
        "type": "normal",
        "weight_kg": 50.0,
        "reps": 8,
        "rpe": None,
        "duration_seconds": None,
        "distance_meters": None,
        "custom_metric": None,
    }
    assert len(result["sessions"][0]["working_sets"]) == 2  # excludes warmup


@pytest.mark.asyncio
async def test_invalid_dates_and_timezone_fail_explicitly() -> None:
    service = TrainingService(DemoHevyClient(), provider="demo")
    with pytest.raises(ValueError, match="on or after"):
        await service.report("2026-11-08", "2026-11-02", "UTC")
    with pytest.raises(ValueError, match="timezone"):
        await service.report("2026-11-02", "2026-11-08", "Not/AZone")


@pytest.mark.asyncio
@respx.mock
async def test_hevy_loads_all_pages_with_official_page_limits() -> None:
    seen: list[int] = []

    def reply(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        seen.append(page)
        assert request.url.params["pageSize"] == "10"
        assert request.headers["api-key"] == "example-key"
        assert "x-api-key" not in request.headers
        return httpx.Response(
            200,
            json={
                "page": page,
                "page_count": 2,
                "workouts": [{"id": f"id-{page}", "start_time": "2026-11-04T18:00:00Z"}],
            },
        )

    respx.get("https://api.hevyapp.com/v1/workouts").mock(side_effect=reply)
    client = HevyClient(Settings(_env_file=None, hevy_api_key="example-key"))
    try:
        workouts = await client.get_all_workouts()
    finally:
        await client.close()
    assert seen == [1, 2]
    assert [w.id for w in workouts] == ["id-1", "id-2"]


@pytest.mark.asyncio
@respx.mock
async def test_hevy_second_page_failure_is_not_an_empty_or_complete_report() -> None:
    def reply(request: httpx.Request) -> httpx.Response:
        if request.url.params["page"] == "1":
            return httpx.Response(200, json={"page": 1, "page_count": 2, "workouts": []})
        return httpx.Response(503)

    respx.get("https://api.hevyapp.com/v1/workouts").mock(side_effect=reply)
    client = HevyClient(Settings(_env_file=None, hevy_api_key="example-key", max_retries=1))
    try:
        with pytest.raises(UpstreamAPIError):
            await TrainingService(client).report("2026-11-02", "2026-11-08", "UTC")
    finally:
        await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_hevy_auth_failure_does_not_expose_response_body() -> None:
    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(401, text="example-secret-that-must-not-be-logged")
    )
    client = HevyClient(Settings(_env_file=None, hevy_api_key="example-key", max_retries=1))
    try:
        with pytest.raises(UpstreamAPIError) as exc:
            await client.get_all_workouts()
        assert "example-secret-that-must-not-be-logged" not in str(exc.value)
    finally:
        await client.close()


def test_unrecognized_hevy_set_type_remains_unknown() -> None:
    client = HevyClient(Settings(_env_file=None))
    assert client._parse_set_type("unrecognized-type") == SetType.UNKNOWN
    assert client._parse_set_type(None) == SetType.UNKNOWN


@pytest.mark.asyncio
@respx.mock
async def test_mcp_report_with_mocked_hevy_api(
    mock_settings: Settings, sample_hevy_workouts_payload: dict[str, Any]
) -> None:
    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_payload)
    )
    respx.get("https://api.hevyapp.com/v1/exercise_templates").mock(
        return_value=httpx.Response(
            200,
            json={
                "page": 1,
                "page_count": 1,
                "exercise_templates": [
                    {
                        "id": "TPL_SQUAT",
                        "title": "Barbell Back Squat",
                        "primary_muscle_group": "quadriceps",
                        "secondary_muscle_groups": ["glutes"],
                    },
                    {
                        "id": "TPL_RDL",
                        "title": "Romanian Deadlift",
                        "primary_muscle_group": "hamstrings",
                        "secondary_muscle_groups": ["glutes"],
                    },
                ],
            },
        )
    )
    server = create_server(TrainingService(HevyClient(mock_settings)))
    async with Client(server) as client:
        result = await client.call_tool(
            "get_training_report",
            {
                "start_date": "2026-11-02",
                "end_date": "2026-11-08",
                "timezone": "UTC",
            },
        )
        assert result.structured_content is not None
        current = result.structured_content["current"]
        assert current["working_sets"] == 5
        assert current["warmup_sets"] == 2
        assert current["muscle_groups"]["primary_working_sets"] == {
            "hamstrings": 2,
            "quadriceps": 3,
        }
        assert current["muscle_groups"]["secondary_involvement_sets"] == {"glutes": 5}
        assert result.structured_content["source"]["provider"] == "hevy"


@pytest.mark.asyncio
async def test_mcp_demo_report_and_tool_contract() -> None:
    server = create_server(TrainingService(DemoHevyClient(), provider="demo"))
    async with Client(server) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools} >= {
            "get_training_report",
            "search_exercises",
            "get_exercise_progression",
            "get_workout_details",
        }
        analytics = {
            "get_training_report",
            "search_exercises",
            "get_exercise_progression",
            "get_workout_details",
        }
        assert all(
            t.annotations and t.annotations.read_only_hint for t in tools if t.name in analytics
        )
        assert all(
            not t.annotations.read_only_hint
            for t in tools
            if t.name.startswith(("create_hevy_", "update_hevy_")) and t.annotations
        )
        result = await client.call_tool(
            "get_training_report",
            {
                "start_date": "2026-11-02",
                "end_date": "2026-11-08",
                "timezone": "UTC",
            },
        )
        assert result.structured_content is not None
        assert result.structured_content["current"]["working_sets"] == 6
        assert result.structured_content["source"]["provider"] == "demo"


@pytest.mark.asyncio
async def test_cached_snapshot_refreshes_only_when_requested() -> None:
    class CountingSource(DemoHevyClient):
        calls = 0

        async def get_all_workouts(self) -> list[WorkoutSession]:
            self.calls += 1
            return await super().get_all_workouts()

    source = CountingSource()
    service = TrainingService(source, cache_seconds=300)
    await service.report("2026-11-02", "2026-11-08", "UTC")
    await service.report("2026-11-02", "2026-11-08", "UTC")
    assert source.calls == 1
    await service.report("2026-11-02", "2026-11-08", "UTC", refresh=True)
    assert source.calls == 2
