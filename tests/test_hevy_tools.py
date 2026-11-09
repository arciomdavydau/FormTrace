"""Contract tests for Hevy API tools; all mutations use a mocked API."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx
from fastmcp import Client
from pydantic import ValidationError

from fitness_hub.clients.base import RateLimitError, UpstreamAPIError
from fitness_hub.clients.hevy import HevyClient
from fitness_hub.config import Settings
from fitness_hub.demo import DemoHevyClient
from fitness_hub.models.hevy_inputs import (
    RoutineUpdateInput,
    WorkoutCreateInput,
    WorkoutUpdateInput,
)
from fitness_hub.server import create_server
from fitness_hub.services.hevy import HevyOperations
from fitness_hub.services.training import TrainingService
from tests.helpers import assert_output_matches_schema


def make_settings() -> Settings:
    return Settings(_env_file=None, hevy_api_key="fictional-test-key", max_retries=3)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "path", "args", "expected_query"),
    [
        ("get_hevy_profile", "user/info", {}, {}),
        (
            "list_hevy_workouts",
            "workouts",
            {"page": 2, "page_size": 7},
            {"page": "2", "pageSize": "7"},
        ),
        ("get_hevy_workout_count", "workouts/count", {}, {}),
        ("get_hevy_workout", "workouts/ABC-123", {"workout_id": "ABC-123"}, {}),
        (
            "list_hevy_workout_events",
            "workouts/events",
            {"since": "2026-01-01T00:00:00Z"},
            {"page": "1", "pageSize": "10", "since": "2026-01-01T00:00:00Z"},
        ),
        ("list_hevy_routines", "routines", {}, {"page": "1", "pageSize": "10"}),
        ("get_hevy_routine", "routines/routine-1", {"routine_id": "routine-1"}, {}),
        (
            "list_hevy_exercise_templates",
            "exercise_templates",
            {},
            {"page": "1", "pageSize": "100"},
        ),
        ("get_hevy_exercise_template", "exercise_templates/ABC", {"exercise_id": "ABC"}, {}),
        ("get_hevy_exercise_history", "exercise_history/ABC", {"exercise_id": "ABC"}, {}),
        ("list_hevy_routine_folders", "routine_folders", {}, {"page": "1", "pageSize": "10"}),
        ("get_hevy_routine_folder", "routine_folders/3", {"folder_id": 3}, {}),
    ],
)
async def test_read_tools_call_the_documented_hevy_endpoints(
    tool: str, path: str, args: dict[str, Any], expected_query: dict[str, str]
) -> None:
    with respx.mock:
        route = respx.get(f"https://api.hevyapp.com/v1/{path}").mock(
            return_value=httpx.Response(200, json={"fictional": True})
        )
        server = create_server(TrainingService(HevyClient(make_settings())))
        async with Client(server) as client:
            result = await client.call_tool(tool, args)
            assert result.structured_content and result.structured_content["data"] == {
                "fictional": True
            }
            await assert_output_matches_schema(client, tool, result.structured_content)
        assert route.call_count == 1
        request = route.calls[0].request
        assert dict(request.url.params) == expected_query
        assert request.headers["api-key"] == "fictional-test-key"


WORKOUT = {
    "title": "Fictional workout",
    "start_time": "2026-11-01T12:00:00Z",
    "end_time": "2026-11-01T13:00:00Z",
    "exercises": [{"exercise_template_id": "AB12", "sets": [{"weight_kg": 40, "reps": 8}]}],
}
ROUTINE = {
    "title": "Fictional routine",
    "exercises": [{"exercise_template_id": "AB12", "sets": [{"reps": 8}]}],
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "method", "path", "wrapper", "args"),
    [
        ("create_hevy_workout", "POST", "workouts", "workout", {"workout": WORKOUT}),
        (
            "update_hevy_workout",
            "PUT",
            "workouts/id-1",
            "workout",
            {"workout_id": "id-1", "workout": {**WORKOUT, "is_private": False}},
        ),
        ("create_hevy_routine", "POST", "routines", "routine", {"routine": ROUTINE}),
        (
            "update_hevy_routine",
            "PUT",
            "routines/id-1",
            "routine",
            {"routine_id": "id-1", "routine": {**ROUTINE, "folder_id": None, "notes": None}},
        ),
        (
            "create_hevy_exercise_template",
            "POST",
            "exercise_templates",
            "exercise",
            {
                "exercise": {
                    "title": "Demo exercise",
                    "exercise_type": "weight_reps",
                    "equipment_category": "barbell",
                    "muscle_group": "chest",
                }
            },
        ),
        (
            "create_hevy_routine_folder",
            "POST",
            "routine_folders",
            "routine_folder",
            {"folder": {"title": "Demo folder"}},
        ),
    ],
)
async def test_write_tools_preview_then_send_expected_payload(
    tool: str, method: str, path: str, wrapper: str, args: dict[str, Any]
) -> None:
    with respx.mock:
        route = respx.route(method=method, url=f"https://api.hevyapp.com/v1/{path}").mock(
            return_value=httpx.Response(200, json={"fictional": True})
        )
        server = create_server(TrainingService(HevyClient(make_settings())))
        async with Client(server) as client:
            preview = await client.call_tool(tool, args)
            assert preview.structured_content and preview.structured_content["dry_run"] is True
            await assert_output_matches_schema(client, tool, preview.structured_content)
            assert route.call_count == 0
            result = await client.call_tool(tool, {**args, "dry_run": False})
            assert result.structured_content and result.structured_content["dry_run"] is False
            await assert_output_matches_schema(client, tool, result.structured_content)
        assert route.call_count == 1
        body = json.loads(route.calls[0].request.content)
        assert wrapper in body
        assert body == preview.structured_content["payload"]
        if wrapper in {"workout", "routine"}:
            assert body[wrapper]["exercises"][0]["sets"][0]["type"] == "normal"
        if tool == "create_hevy_workout":
            assert body["workout"]["is_private"] is True
        if tool == "update_hevy_workout":
            assert body["workout"]["is_private"] is False
        if tool == "update_hevy_routine":
            assert body["routine"]["folder_id"] is None and body["routine"]["notes"] is None
        if tool == "create_hevy_routine":
            assert body["routine"]["folder_id"] is None


def test_full_updates_require_fields_that_could_otherwise_be_overwritten() -> None:
    with pytest.raises(ValidationError):
        WorkoutUpdateInput.model_validate(WORKOUT)
    with pytest.raises(ValidationError):
        RoutineUpdateInput.model_validate(ROUTINE)
    with pytest.raises(ValidationError):
        WorkoutCreateInput.model_validate({**WORKOUT, "start_time": "2026-11-01T12:00:00"})
    bad_set = {**WORKOUT, "exercises": [{"exercise_template_id": "X", "sets": [{"rpe": 6.5}]}]}
    with pytest.raises(ValidationError):
        WorkoutCreateInput.model_validate(bad_set)


@pytest.mark.asyncio
@respx.mock
async def test_failed_write_is_not_retried_and_invalidates_snapshot() -> None:
    route = respx.post("https://api.hevyapp.com/v1/workouts").mock(return_value=httpx.Response(503))
    source = HevyClient(make_settings())
    training = TrainingService(source)
    operations = HevyOperations(training)
    try:
        with pytest.raises(UpstreamAPIError, match="may have succeeded"):
            await operations.write(
                "POST",
                "workouts",
                "workout",
                WorkoutCreateInput.model_validate(WORKOUT),
                dry_run=False,
            )
        assert route.call_count == 1
        assert training._snapshot is None
    finally:
        await training.close()


@pytest.mark.asyncio
@respx.mock
async def test_timed_out_write_is_not_automatically_retried() -> None:
    route = respx.post("https://api.hevyapp.com/v1/workouts").mock(
        side_effect=httpx.ReadTimeout("test timeout")
    )
    source = HevyClient(make_settings())
    try:
        with pytest.raises(UpstreamAPIError, match="may have succeeded"):
            await HevyOperations(TrainingService(source)).write(
                "POST",
                "workouts",
                "workout",
                WorkoutCreateInput.model_validate(WORKOUT),
                dry_run=False,
            )
        assert route.call_count == 1
    finally:
        await source.close()


@pytest.mark.asyncio
@respx.mock
async def test_transient_read_can_be_retried() -> None:
    route = respx.get("https://api.hevyapp.com/v1/workouts/count").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"workout_count": 2})]
    )
    source = HevyClient(make_settings())
    source.backoff_factor = 0
    try:
        result = await source.api_request("GET", "workouts/count")
        assert result == {"workout_count": 2}
        assert route.call_count == 2
    finally:
        await source.close()


@pytest.mark.asyncio
@respx.mock
async def test_rate_limited_read_retries_without_repeating_writes() -> None:
    read = respx.get("https://api.hevyapp.com/v1/workouts/count").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"workout_count": 2}),
        ]
    )
    write = respx.post("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0"})
    )
    source = HevyClient(make_settings())
    source.backoff_factor = 0
    try:
        assert (await source.api_request("GET", "workouts/count"))["workout_count"] == 2
        with pytest.raises(RateLimitError):
            await HevyOperations(TrainingService(source)).write(
                "POST",
                "workouts",
                "workout",
                WorkoutCreateInput.model_validate(WORKOUT),
                dry_run=False,
            )
        assert read.call_count == 2
        assert write.call_count == 1
    finally:
        await source.close()


@pytest.mark.asyncio
@respx.mock
async def test_invalid_write_response_warns_that_the_operation_may_have_succeeded() -> None:
    route = respx.post("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, text="not JSON")
    )
    source = HevyClient(make_settings())
    try:
        with pytest.raises(UpstreamAPIError, match="may have succeeded"):
            await HevyOperations(TrainingService(source)).write(
                "POST",
                "workouts",
                "workout",
                WorkoutCreateInput.model_validate(WORKOUT),
                dry_run=False,
            )
        assert route.call_count == 1
    finally:
        await source.close()


@pytest.mark.asyncio
@respx.mock
async def test_create_exercise_accepts_hevys_plain_text_identifier() -> None:
    route = respx.post("https://api.hevyapp.com/v1/exercise_templates").mock(
        return_value=httpx.Response(
            200, text="01234567-89ab-4cde-8fab-0123456789ab", headers={"content-type": "text/html"}
        )
    )
    server = create_server(TrainingService(HevyClient(make_settings())))
    async with Client(server) as client:
        result = await client.call_tool(
            "create_hevy_exercise_template",
            {
                "dry_run": False,
                "exercise": {
                    "title": "test exercise",
                    "exercise_type": "weight_reps",
                    "equipment_category": "barbell",
                    "muscle_group": "chest",
                },
            },
        )
        assert (
            result.structured_content
            and result.structured_content["data"]["id"] == "01234567-89ab-4cde-8fab-0123456789ab"
        )
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_unexpected_plain_text_is_not_reported_as_an_exercise_id() -> None:
    route = respx.post("https://api.hevyapp.com/v1/exercise_templates").mock(
        return_value=httpx.Response(200, text="FAILED")
    )
    source = HevyClient(make_settings())
    try:
        with pytest.raises(UpstreamAPIError, match="may have succeeded"):
            await source.api_request("POST", "exercise_templates", body={"exercise": {}})
        assert route.call_count == 1
    finally:
        await source.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("get_hevy_workout", {"workout_id": "../routines"}),
        ("list_hevy_workouts", {"page": 0}),
        ("list_hevy_workouts", {"page_size": 11}),
        ("list_hevy_workout_events", {"since": "2026-11-01T12:00:00"}),
        (
            "get_hevy_exercise_history",
            {
                "exercise_id": "X",
                "start_date": "2026-11-02T00:00:00Z",
                "end_date": "2026-11-01T00:00:00Z",
            },
        ),
    ],
)
async def test_invalid_read_arguments_fail_without_contacting_hevy(
    tool: str, args: dict[str, Any]
) -> None:
    with respx.mock:
        server = create_server(TrainingService(HevyClient(make_settings())))
        async with Client(server) as client:
            result = await client.call_tool(tool, args, raise_on_error=False)
            assert result.is_error


@pytest.mark.asyncio
@pytest.mark.parametrize("write_fails", [False, True])
async def test_cached_analytics_are_invalidated_after_write_attempt(write_fails: bool) -> None:
    class Source(DemoHevyClient):
        calls = 0

        async def get_all_workouts(self) -> list[Any]:
            self.calls += 1
            return await super().get_all_workouts()

        async def api_request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
            if write_fails:
                raise UpstreamAPIError("The write may have succeeded")
            return {"ok": True}

    source = Source()
    training = TrainingService(source)
    await training.report("2026-11-02", "2026-11-08", "UTC")
    assert source.calls == 1
    operations = HevyOperations(training)
    payload = WorkoutCreateInput.model_validate(WORKOUT)
    await operations.write("POST", "workouts", "workout", payload, dry_run=True)
    await training.report("2026-11-02", "2026-11-08", "UTC")
    assert source.calls == 1  # a preview does not invalidate the cache
    if write_fails:
        with pytest.raises(UpstreamAPIError):
            await operations.write("POST", "workouts", "workout", payload, dry_run=False)
    else:
        await operations.write("POST", "workouts", "workout", payload, dry_run=False)
    await training.report("2026-11-02", "2026-11-08", "UTC")
    assert source.calls == 2


@pytest.mark.asyncio
async def test_read_and_write_annotations_match_the_tool_effects() -> None:
    server = create_server(TrainingService(DemoHevyClient(), provider="demo"))
    async with Client(server) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        assert len(tools) == 22
        assert tools["get_hevy_routine"].annotations.read_only_hint is True
        assert tools["create_hevy_routine"].annotations.read_only_hint is False
        assert tools["update_hevy_routine"].annotations.destructive_hint is True


@pytest.mark.asyncio
async def test_demo_mode_supports_reading_and_previews_but_never_live_writes() -> None:
    server = create_server(TrainingService(DemoHevyClient(), provider="demo"))
    async with Client(server) as client:
        result = await client.call_tool("list_hevy_workouts", {})
        assert result.structured_content and len(result.structured_content["data"]["workouts"]) == 2
        preview = await client.call_tool("create_hevy_workout", {"workout": WORKOUT})
        assert preview.structured_content and preview.structured_content["dry_run"] is True
        failure = await client.call_tool(
            "create_hevy_workout", {"workout": WORKOUT, "dry_run": False}, raise_on_error=False
        )
        assert failure.is_error
