"""Tests verifying deterministic working tonnage math, warmup exclusion, and Hevy model parsing."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from fitness_hub.clients.hevy import HevyClient
from fitness_hub.models.workouts import (
    ExerciseLog,
    ExerciseSet,
    SetType,
    WorkoutSession,
)


def test_working_tonnage_excludes_warmup_sets() -> None:
    """Verify that warmup sets are strictly excluded while normal/failure/dropset sets are included."""
    exercise = ExerciseLog(
        title="Barbell Back Squat",
        sets=[
            # Warmup sets - should NOT contribute to working volume or working sets count
            ExerciseSet(index=0, set_type=SetType.WARMUP, weight_kg=60.0, reps=10, rpe=None),
            ExerciseSet(index=1, set_type=SetType.WARMUP, weight_kg=100.0, reps=5, rpe=None),
            # Working sets
            ExerciseSet(
                index=2, set_type=SetType.NORMAL, weight_kg=140.0, reps=8, rpe=8.0
            ),  # 1120 kg
            ExerciseSet(
                index=3, set_type=SetType.NORMAL, weight_kg=140.0, reps=8, rpe=8.5
            ),  # 1120 kg
            ExerciseSet(
                index=4, set_type=SetType.FAILURE, weight_kg=140.0, reps=6, rpe=10.0
            ),  # 840 kg
            ExerciseSet(
                index=5, set_type=SetType.DROPSET, weight_kg=100.0, reps=10, rpe=9.0
            ),  # 1000 kg
        ],
    )

    # Working sets count should be 4 (excluding 2 warmups)
    assert exercise.total_working_sets == 4

    # Working tonnage = 1120 + 1120 + 840 + 1000 = 4080 kg
    assert exercise.working_tonnage_kg == 4080.0

    # Average RPE across working sets: (8.0 + 8.5 + 10.0 + 9.0) / 4 = 8.88
    assert exercise.avg_rpe == 8.88


def test_sets_with_missing_weight_or_reps_do_not_crash() -> None:
    """Verify sets with None weight or reps contribute 0 to tonnage without crashing."""
    exercise = ExerciseLog(
        title="Bodyweight Pull-Up",
        sets=[
            ExerciseSet(index=0, set_type=SetType.NORMAL, weight_kg=None, reps=12, rpe=8.0),
            ExerciseSet(index=1, set_type=SetType.NORMAL, weight_kg=20.0, reps=None, rpe=8.0),
            ExerciseSet(
                index=2, set_type=SetType.NORMAL, weight_kg=20.0, reps=8, rpe=8.5
            ),  # 160 kg
        ],
    )
    assert exercise.total_working_sets == 3
    assert exercise.working_tonnage_kg == 160.0


def test_workout_session_aggregate_tonnage(sample_workout_session: WorkoutSession) -> None:
    """Verify session-level aggregation of volume and working sets."""
    # Bench Press:
    # Warmup 60x12 (0), Normal 100x8 (800), Failure 100x6 (600) -> 1400 kg, 2 working sets
    # Overhead Press:
    # Normal 60x8 (480), Dropset 50x10 (500) -> 980 kg, 2 working sets
    # Total Tonnage: 1400 + 980 = 2380 kg
    assert sample_workout_session.working_tonnage_kg == 2380.0
    assert sample_workout_session.total_working_sets == 4

    # Avg RPE across working sets: (8.0 + 10.0 + 8.5 + 9.0) / 4 = 8.88
    assert sample_workout_session.avg_rpe == 8.88
    assert sample_workout_session.duration_minutes == 75.0


@pytest.mark.asyncio
@respx.mock
async def test_hevy_client_parses_nested_payload(
    hevy_client: HevyClient,
    sample_hevy_workouts_payload: dict[str, Any],
) -> None:
    """Verify HevyClient parses raw nested JSON into typed WorkoutSession with correct tonnage."""
    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_payload)
    )

    workouts = await hevy_client.get_recent_workouts(limit=1)
    assert len(workouts) == 1

    w = workouts[0]
    assert w.id == "workout-uuid-001"
    assert w.title == "Leg Day Hypertrophy"
    assert len(w.exercises) == 2

    # Squat working volume:
    # 2 warmups excluded
    # 140x8 (1120) + 140x8 (1120) + 140x7 (980) = 3220 kg
    squat = w.exercises[0]
    assert squat.working_tonnage_kg == 3220.0
    assert squat.total_working_sets == 3

    # RDL working volume:
    # 110x10 (1100) + 90x12 (1080) = 2180 kg
    rdl = w.exercises[1]
    assert rdl.working_tonnage_kg == 2180.0
    assert rdl.total_working_sets == 2

    # Total Session Tonnage: 3220 + 2180 = 5400 kg
    assert w.working_tonnage_kg == 5400.0
    assert w.total_working_sets == 5
    assert w.avg_rpe == 8.8  # (8.0 + 8.5 + 10.0 + 8.0 + 9.5) / 5 = 8.8
