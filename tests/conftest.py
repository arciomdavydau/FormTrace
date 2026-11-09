"""Shared pytest fixtures, realistic mock payloads, and test client factories."""

from __future__ import annotations

from typing import Any

import pytest

from fitness_hub.clients.hevy import HevyClient
from fitness_hub.clients.nutrition import NutritionAdapter
from fitness_hub.clients.wearables import WearablesClient
from fitness_hub.config import Settings
from fitness_hub.models.workouts import (
    ExerciseLog,
    ExerciseSet,
    SetType,
    WorkoutSession,
)


@pytest.fixture
def mock_settings(tmp_path: Any) -> Settings:
    """Isolated settings instance using temporary files and mock endpoints."""
    nutrition_path = tmp_path / "test_nutrition_logs.json"
    return Settings(
        mcp_server_name="test-fitness-mcp-hub",
        mcp_transport="stdio",
        open_wearables_base_url="http://localhost:8080",
        open_wearables_api_key="mock-wearables-api-key",
        hevy_api_base_url="https://api.hevyapp.com/v1",
        hevy_api_key="mock-hevy-api-key",
        nutrition_provider="local",
        nutrition_data_path=str(nutrition_path),
        target_daily_calories=2200,
        target_protein_g=180,
        target_daily_steps=9000,
        request_timeout=5.0,
        max_retries=2,
    )


@pytest.fixture
def sample_wearables_activity_payload() -> dict[str, Any]:
    """Realistic JSON response for GET /api/v1/activity/{date}."""
    return {
        "date": "2026-11-09",
        "steps": 10450,
        "active_calories": 520,
        "resting_hr_bpm": 56,
        "distance_meters": 7820.5,
    }


@pytest.fixture
def sample_wearables_sleep_payload() -> dict[str, Any]:
    """Realistic JSON response for GET /api/v1/sleep/{date}."""
    return {
        "date": "2026-11-09",
        "total_sleep_minutes": 465,  # 7.75 hours (> 450 min baseline)
        "deep_sleep_minutes": 105,
        "rem_sleep_minutes": 120,
        "sleep_efficiency_pct": 92.5,
        "resting_hr_bpm": 54,
        "hrv_sdnn_ms": 68.2,
    }


@pytest.fixture
def sample_hevy_workouts_payload() -> dict[str, Any]:
    """Realistic JSON payload from Hevy API GET /workouts."""
    return {
        "page": 1,
        "page_count": 1,
        "workouts": [
            {
                "id": "workout-uuid-001",
                "title": "Leg Day Hypertrophy",
                "description": "Squat focus and posterior chain",
                "start_time": "2026-11-08T18:00:00Z",
                "end_time": "2026-11-08T19:15:00Z",
                "exercises": [
                    {
                        "id": "ex-squat-1",
                        "title": "Barbell Back Squat",
                        "exercise_template_id": "TPL_SQUAT",
                        "notes": "Good depth, controlled tempo",
                        "sets": [
                            {
                                "index": 0,
                                "type": "warmup",
                                "weight_kg": 60.0,
                                "reps": 10,
                                "rpe": None,
                            },
                            {
                                "index": 1,
                                "type": "warmup",
                                "weight_kg": 100.0,
                                "reps": 5,
                                "rpe": None,
                            },
                            {
                                "index": 2,
                                "type": "normal",
                                "weight_kg": 140.0,
                                "reps": 8,
                                "rpe": 8.0,
                            },
                            {
                                "index": 3,
                                "type": "normal",
                                "weight_kg": 140.0,
                                "reps": 8,
                                "rpe": 8.5,
                            },
                            {
                                "index": 4,
                                "type": "failure",
                                "weight_kg": 140.0,
                                "reps": 7,
                                "rpe": 10.0,
                            },
                        ],
                    },
                    {
                        "id": "ex-rdl-2",
                        "title": "Romanian Deadlift",
                        "exercise_template_id": "TPL_RDL",
                        "notes": None,
                        "sets": [
                            {
                                "index": 0,
                                "type": "normal",
                                "weight_kg": 110.0,
                                "reps": 10,
                                "rpe": 8.0,
                            },
                            {
                                "index": 1,
                                "type": "dropset",
                                "weight_kg": 90.0,
                                "reps": 12,
                                "rpe": 9.5,
                            },
                        ],
                    },
                ],
            }
        ],
    }


@pytest.fixture
def sample_workout_session() -> WorkoutSession:
    """Pre-built domain WorkoutSession with known sets and weights."""
    return WorkoutSession(
        id="sample-sess-01",
        title="Push Day Strength",
        start_time="2026-11-08T16:00:00Z",
        end_time="2026-11-08T17:15:00Z",
        exercises=[
            ExerciseLog(
                title="Bench Press",
                sets=[
                    ExerciseSet(index=0, set_type=SetType.WARMUP, weight_kg=60.0, reps=12),
                    ExerciseSet(index=1, set_type=SetType.NORMAL, weight_kg=100.0, reps=8, rpe=8.0),
                    ExerciseSet(
                        index=2, set_type=SetType.FAILURE, weight_kg=100.0, reps=6, rpe=10.0
                    ),
                ],
            ),
            ExerciseLog(
                title="Overhead Press",
                sets=[
                    ExerciseSet(index=0, set_type=SetType.NORMAL, weight_kg=60.0, reps=8, rpe=8.5),
                    ExerciseSet(
                        index=1, set_type=SetType.DROPSET, weight_kg=50.0, reps=10, rpe=9.0
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def wearables_client(mock_settings: Settings) -> WearablesClient:
    return WearablesClient(settings=mock_settings)


@pytest.fixture
def hevy_client(mock_settings: Settings) -> HevyClient:
    return HevyClient(settings=mock_settings)


@pytest.fixture
def nutrition_adapter(mock_settings: Settings) -> NutritionAdapter:
    return NutritionAdapter(settings=mock_settings)
