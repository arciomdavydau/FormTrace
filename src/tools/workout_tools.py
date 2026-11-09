"""MCP tools for tracking Hevy strength workouts, exercises, working sets, RPE, and volume."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from src.clients.hevy import HevyClient

logger = logging.getLogger(__name__)

workout_router = FastMCP(name="Workout Tools")
_client: HevyClient | None = None


def get_hevy_client() -> HevyClient:
    """Get or instantiate singleton HevyClient."""
    global _client
    if _client is None:
        _client = HevyClient()
    return _client


def set_hevy_client(client: HevyClient | None) -> None:
    """Override client for testing/injection."""
    global _client
    _client = client


@workout_router.tool
async def get_recent_workouts(
    page: int = 1,
    page_size: int = 10,
    since: str | None = None,
) -> dict[str, Any]:
    """
    Get recent logged strength workouts from Hevy.

    Args:
        page: Page number (starts at 1)
        page_size: Number of workouts per page (1 to 10)
        since: Optional ISO 8601 date to filter recent workouts
    """
    client = get_hevy_client()
    workouts = await client.get_workouts(page=page, page_size=page_size, since=since)

    return {
        "page": page,
        "count": len(workouts),
        "workouts": [
            {
                "id": w.id,
                "title": w.title,
                "start_time": w.start_time,
                "end_time": w.end_time,
                "duration_minutes": w.duration_minutes,
                "total_tonnage_kg": w.total_tonnage_kg,
                "working_sets_count": w.total_working_sets,
                "avg_rpe": w.avg_rpe,
                "exercises_count": len(w.exercises),
                "exercise_titles": [ex.title for ex in w.exercises],
            }
            for w in workouts
        ],
    }


@workout_router.tool
async def get_workout_details(workout_id: str) -> dict[str, Any]:
    """
    Get detailed breakdown of a specific workout including all exercises, sets, weights, reps, and RPE.

    Args:
        workout_id: The UUID of the workout
    """
    client = get_hevy_client()
    workout = await client.get_workout(workout_id)

    exercises_detail = []
    for ex in workout.exercises:
        exercises_detail.append(
            {
                "id": ex.id,
                "title": ex.title,
                "exercise_template_id": ex.exercise_template_id,
                "notes": ex.notes,
                "total_volume_kg": ex.total_volume_kg,
                "working_sets_count": ex.working_sets_count,
                "max_weight_kg": ex.max_weight_kg,
                "best_estimated_1rm_kg": ex.best_estimated_1rm,
                "avg_rpe": ex.avg_rpe,
                "sets": [s.model_dump() for s in ex.sets],
            }
        )

    return {
        "id": workout.id,
        "title": workout.title,
        "description": workout.description,
        "start_time": workout.start_time,
        "end_time": workout.end_time,
        "duration_minutes": workout.duration_minutes,
        "total_tonnage_kg": workout.total_tonnage_kg,
        "total_working_sets": workout.total_working_sets,
        "avg_rpe": workout.avg_rpe,
        "exercises": exercises_detail,
    }


@workout_router.tool
async def get_workout_volume_analytics(
    page_size: int = 20,
    since: str | None = None,
) -> dict[str, Any]:
    """
    Calculate volume tonnage and workload analytics across recent training sessions.

    Args:
        page_size: Number of recent workouts to analyze (default: 20)
        since: Optional ISO 8601 start timestamp
    """
    client = get_hevy_client()
    summary = await client.get_workout_summary(page_size=page_size, since=since)

    # Exercise frequency and best 1RM mapping
    exercise_counts: dict[str, int] = {}
    exercise_max_weights: dict[str, float] = {}
    exercise_estimated_1rms: dict[str, float] = {}

    for w in summary.workouts:
        for ex in w.exercises:
            name = ex.title
            exercise_counts[name] = exercise_counts.get(name, 0) + 1
            if ex.max_weight_kg is not None:
                curr_max = exercise_max_weights.get(name, 0.0)
                if ex.max_weight_kg > curr_max:
                    exercise_max_weights[name] = ex.max_weight_kg
            if ex.best_estimated_1rm is not None:
                curr_1rm = exercise_estimated_1rms.get(name, 0.0)
                if ex.best_estimated_1rm > curr_1rm:
                    exercise_estimated_1rms[name] = ex.best_estimated_1rm

    most_frequent = [
        {"exercise": k, "frequency": v}
        for k, v in sorted(exercise_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    ]

    return {
        "total_workouts_analyzed": summary.total_workouts,
        "period_start": summary.period_start,
        "period_end": summary.period_end,
        "total_tonnage_kg": summary.total_tonnage_kg,
        "avg_tonnage_per_workout_kg": (
            round(summary.total_tonnage_kg / summary.total_workouts, 1)
            if summary.total_workouts
            else 0.0
        ),
        "total_working_sets": summary.total_working_sets,
        "avg_working_sets_per_workout": (
            round(summary.total_working_sets / summary.total_workouts, 1)
            if summary.total_workouts
            else 0.0
        ),
        "avg_workout_rpe": summary.avg_workout_rpe,
        "most_frequent_exercises": most_frequent,
        "max_weights_kg": exercise_max_weights,
        "estimated_1rms_kg": exercise_estimated_1rms,
    }


@workout_router.tool
async def log_workout_session(
    title: str,
    exercises: list[dict[str, Any]],
    start_time: str,
    end_time: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    """
    Log a completed workout session to Hevy.

    Args:
        title: Workout title (e.g. 'Push Day A')
        exercises: List of exercise dicts with 'exercise_template_id' and 'sets'
        start_time: ISO 8601 timestamp when workout started
        end_time: Optional ISO 8601 timestamp when workout ended
        description: Optional notes on the workout session
    """
    client = get_hevy_client()
    payload = {
        "title": title,
        "description": description,
        "start_time": start_time,
        "end_time": end_time,
        "exercises": exercises,
    }
    result = await client.create_workout(payload)
    return {
        "status": "created",
        "id": result.id,
        "title": result.title,
        "total_tonnage_kg": result.total_tonnage_kg,
        "total_working_sets": result.total_working_sets,
    }
