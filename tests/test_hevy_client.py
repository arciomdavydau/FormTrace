"""Unit tests for HevyClient with respx HTTP mocking."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from pydantic import SecretStr

from src.clients.base import ConfigurationError
from src.clients.hevy import HevyClient
from src.config import Settings


@pytest.mark.asyncio
async def test_hevy_client_unconfigured() -> None:
    """Client should raise ConfigurationError when no API key is provided."""
    unconfigured_settings = Settings(hevy_api_key=SecretStr(""))
    client = HevyClient(settings=unconfigured_settings)
    with pytest.raises(ConfigurationError):
        await client.get_workouts()


@pytest.mark.asyncio
@respx.mock
async def test_hevy_client_get_workout_count(hevy_client: HevyClient) -> None:
    """Test fetching total workout count."""
    respx.get("https://test-hevy.local/v1/workouts/count").mock(
        return_value=httpx.Response(200, json={"workout_count": 42})
    )
    count = await hevy_client.get_workout_count()
    assert count == 42


@pytest.mark.asyncio
@respx.mock
async def test_hevy_client_get_workouts_parsing_and_tonnage(
    hevy_client: HevyClient,
    sample_hevy_workouts_response: dict[str, Any],
) -> None:
    """Test workouts parsing, working set classification, and tonnage calculation."""
    respx.get("https://test-hevy.local/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_response)
    )

    workouts = await hevy_client.get_workouts(page=1, page_size=5)
    assert len(workouts) == 1
    w = workouts[0]
    assert w.id == "hevy-workout-101"
    assert w.title == "Upper Body Strength (A)"
    assert w.duration_minutes == 75.0  # 17:00 to 18:15 = 75 minutes

    # Check Bench Press
    bench = w.exercises[0]
    assert bench.title == "Barbell Bench Press"
    assert len(bench.sets) == 4
    # Warmup set: 60kg * 12 reps -> excluded from working volume
    assert bench.sets[0].type == "warmup"
    assert bench.sets[0].is_working_set is False
    assert bench.sets[0].volume_kg == 0.0

    # Working set 1: 100kg * 8 reps = 800kg
    assert bench.sets[1].type == "normal"
    assert bench.sets[1].is_working_set is True
    assert bench.sets[1].volume_kg == 800.0

    # Working set 2: 100kg * 7 reps = 700kg
    assert bench.sets[2].volume_kg == 700.0

    # Working set 3 (failure): 95kg * 8 reps = 760kg
    assert bench.sets[3].type == "failure"
    assert bench.sets[3].is_working_set is True
    assert bench.sets[3].volume_kg == 760.0

    # Total Bench tonnage: 800 + 700 + 760 = 2260 kg
    assert bench.total_volume_kg == 2260.0
    assert bench.working_sets_count == 3
    assert bench.max_weight_kg == 100.0
    # Estimated 1RM for 100kg x 8 reps = 100 * (1 + 8/30) = 126.67 kg
    assert bench.best_estimated_1rm == 126.67
    assert bench.avg_rpe == 8.83  # (8.0 + 8.5 + 10.0) / 3

    # Check Incline Dumbbell Press: 36kg * 10 reps (360) + 36kg * 9 reps (324) = 684 kg
    incline = w.exercises[1]
    assert incline.total_volume_kg == 684.0
    assert incline.working_sets_count == 2

    # Total Workout Tonnage: 2260 + 684 = 2944 kg
    assert w.total_tonnage_kg == 2944.0
    assert w.total_working_sets == 5
    assert w.avg_rpe == 8.54


@pytest.mark.asyncio
@respx.mock
async def test_hevy_client_get_workout_summary(
    hevy_client: HevyClient,
    sample_hevy_workouts_response: dict[str, Any],
) -> None:
    """Test aggregate workout summary metrics."""
    respx.get("https://test-hevy.local/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_response)
    )

    summary = await hevy_client.get_workout_summary()
    assert summary.total_workouts == 1
    assert summary.total_tonnage_kg == 2944.0
    assert summary.total_working_sets == 5
    assert summary.period_start == "2026-11-09"
    assert summary.period_end == "2026-11-09"


@pytest.mark.asyncio
@respx.mock
async def test_hevy_client_create_workout(hevy_client: HevyClient) -> None:
    """Test creating/logging a workout."""
    payload = {
        "title": "Leg Day",
        "start_time": "2026-11-09T18:00:00Z",
        "exercises": [
            {
                "exercise_template_id": "SQ01",
                "title": "Squat",
                "sets": [{"type": "normal", "weight_kg": 140.0, "reps": 5, "rpe": 8.0}],
            }
        ],
    }

    respx.post("https://test-hevy.local/v1/workouts").mock(
        return_value=httpx.Response(
            201,
            json={
                "workout": {
                    "id": "new-workout-uuid",
                    "title": "Leg Day",
                    "start_time": "2026-11-09T18:00:00Z",
                    "exercises": [
                        {
                            "id": "e-1",
                            "title": "Squat",
                            "sets": [{"type": "normal", "weight_kg": 140.0, "reps": 5}],
                        }
                    ],
                }
            },
        )
    )

    created = await hevy_client.create_workout(payload)
    assert created.id == "new-workout-uuid"
    assert created.title == "Leg Day"
    assert created.total_tonnage_kg == 700.0  # 140 * 5
