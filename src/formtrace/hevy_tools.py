"""MCP tools for the training-related Hevy public API."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from formtrace.models.hevy_inputs import (
    ExerciseCreateInput,
    RoutineCreateInput,
    RoutineFolderCreateInput,
    RoutineUpdateInput,
    WorkoutCreateInput,
    WorkoutUpdateInput,
)
from formtrace.models.responses import HEVY_WRITE_OUTPUT_SCHEMA, HevyReadResult
from formtrace.services.hevy import HevyOperations, aware_timestamp, page_params, resource_id
from formtrace.services.training import TrainingService


def register_hevy_tools(server: FastMCP, training: TrainingService) -> None:
    operations = HevyOperations(training)
    read_only = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True}
    creates = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}
    updates = {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": True}

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def get_hevy_profile() -> dict[str, Any]:
        """Get the authenticated Hevy user's profile and preferred units."""
        return await operations.read("user/info")

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def list_hevy_workouts(page: int = 1, page_size: int = 10) -> dict[str, Any]:
        """Get a page of recorded Hevy workouts; page_size is at most 10."""
        return await operations.read("workouts", params=page_params(page, page_size, 10))

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def get_hevy_workout_count() -> dict[str, Any]:
        """Get the total number of recorded workouts in the Hevy account."""
        return await operations.read("workouts/count")

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def get_hevy_workout(workout_id: str) -> dict[str, Any]:
        """Fetch one recorded workout directly from Hevy by its ID."""
        return await operations.read(f"workouts/{resource_id(workout_id)}")

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def list_hevy_workout_events(
        since: str, page: int = 1, page_size: int = 10
    ) -> dict[str, Any]:
        """Get a page of workout update/delete events since an ISO timestamp with timezone."""
        aware_timestamp(since)
        return await operations.read(
            "workouts/events", params={**page_params(page, page_size, 10), "since": since}
        )

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def list_hevy_routines(page: int = 1, page_size: int = 10) -> dict[str, Any]:
        """Get a page of saved Hevy routines; page_size is at most 10."""
        return await operations.read("routines", params=page_params(page, page_size, 10))

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def get_hevy_routine(routine_id: str) -> dict[str, Any]:
        """Get a saved routine and its exercises by ID."""
        return await operations.read(f"routines/{resource_id(routine_id)}")

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def list_hevy_exercise_templates(page: int = 1, page_size: int = 100) -> dict[str, Any]:
        """Get a page of available Hevy exercise templates; page_size is at most 100."""
        return await operations.read("exercise_templates", params=page_params(page, page_size, 100))

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def get_hevy_exercise_template(exercise_id: str) -> dict[str, Any]:
        """Get one Hevy exercise template, including its muscle classifications."""
        return await operations.read(f"exercise_templates/{resource_id(exercise_id)}")

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def get_hevy_exercise_history(
        exercise_id: str, start_date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Get Hevy's exercise history, optionally filtered by ISO timestamps with timezones."""
        start = aware_timestamp(start_date) if start_date else None
        end = aware_timestamp(end_date) if end_date else None
        if start is not None and end is not None and start > end:
            raise ValueError("end_date must not be before start_date")
        return await operations.read(
            f"exercise_history/{resource_id(exercise_id)}",
            params={"start_date": start_date, "end_date": end_date},
        )

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def list_hevy_routine_folders(page: int = 1, page_size: int = 10) -> dict[str, Any]:
        """Get a page of Hevy routine folders; page_size is at most 10."""
        return await operations.read("routine_folders", params=page_params(page, page_size, 10))

    @server.tool(annotations=read_only, output_schema=HevyReadResult.model_json_schema())
    async def get_hevy_routine_folder(folder_id: int) -> dict[str, Any]:
        """Get a Hevy routine folder by its numeric ID."""
        if folder_id < 0:
            raise ValueError("folder_id must not be negative")
        return await operations.read(f"routine_folders/{folder_id}")

    @server.tool(annotations=creates, output_schema=HEVY_WRITE_OUTPUT_SCHEMA)
    async def create_hevy_workout(
        workout: WorkoutCreateInput, dry_run: bool = True
    ) -> dict[str, Any]:
        """Preview or create a recorded workout. Set dry_run=false to write to Hevy.

        Use timezone-aware timestamps and explicit exercise template IDs. New workouts are
        private by default. Only execute a write when the user has requested it.
        """
        return await operations.write("POST", "workouts", "workout", workout, dry_run=dry_run)

    @server.tool(annotations=updates, output_schema=HEVY_WRITE_OUTPUT_SCHEMA)
    async def update_hevy_workout(
        workout_id: str, workout: WorkoutUpdateInput, dry_run: bool = True
    ) -> dict[str, Any]:
        """Preview or replace a recorded workout. This is a full update, not a partial patch.

        Supply all desired fields and an explicit privacy setting. Set dry_run=false to write;
        only execute a write when the user has requested it.
        """
        return await operations.write(
            "PUT", f"workouts/{resource_id(workout_id)}", "workout", workout, dry_run=dry_run
        )

    @server.tool(annotations=creates, output_schema=HEVY_WRITE_OUTPUT_SCHEMA)
    async def create_hevy_routine(
        routine: RoutineCreateInput, dry_run: bool = True
    ) -> dict[str, Any]:
        """Preview or create a Hevy routine. Set dry_run=false to write to Hevy.

        Only execute a write when the user has requested it.
        """
        return await operations.write("POST", "routines", "routine", routine, dry_run=dry_run)

    @server.tool(annotations=updates, output_schema=HEVY_WRITE_OUTPUT_SCHEMA)
    async def update_hevy_routine(
        routine_id: str, routine: RoutineUpdateInput, dry_run: bool = True
    ) -> dict[str, Any]:
        """Preview or replace a complete routine, including folder, notes, and all exercises.

        Set dry_run=false to write; only execute a write when the user has requested it.
        """
        return await operations.write(
            "PUT", f"routines/{resource_id(routine_id)}", "routine", routine, dry_run=dry_run
        )

    @server.tool(annotations=creates, output_schema=HEVY_WRITE_OUTPUT_SCHEMA)
    async def create_hevy_exercise_template(
        exercise: ExerciseCreateInput, dry_run: bool = True
    ) -> dict[str, Any]:
        """Preview or create a custom Hevy exercise. Set dry_run=false to write to Hevy.

        Only execute a write when the user has requested it.
        """
        return await operations.write(
            "POST", "exercise_templates", "exercise", exercise, dry_run=dry_run
        )

    @server.tool(annotations=creates, output_schema=HEVY_WRITE_OUTPUT_SCHEMA)
    async def create_hevy_routine_folder(
        folder: RoutineFolderCreateInput, dry_run: bool = True
    ) -> dict[str, Any]:
        """Preview or create a routine folder; Hevy inserts it before existing folders.

        Set dry_run=false to write; only execute a write when the user has requested it.
        """
        return await operations.write(
            "POST", "routine_folders", "routine_folder", folder, dry_run=dry_run
        )
