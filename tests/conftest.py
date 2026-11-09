"""Synthetic Hevy payload and isolated configuration for tests."""

from typing import Any

import pytest

from fitness_hub.config import Settings


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        _env_file=None,
        mcp_server_name="test-fitness-mcp-hub",
        hevy_api_base_url="https://api.hevyapp.com/v1",
        hevy_api_key="mock-hevy-api-key",
        request_timeout=5.0,
        max_retries=2,
    )


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
