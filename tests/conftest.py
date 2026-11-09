"""Pytest fixtures and configuration for fitness-mcp-server testing."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import SecretStr

from src.clients.hevy import HevyClient
from src.clients.nutrition import NutritionClient
from src.clients.wearables import OpenWearablesClient
from src.config import Settings


@pytest.fixture
def mock_settings(tmp_path: Any) -> Settings:
    """Provide isolated Settings instance for unit tests."""
    data_file = tmp_path / "test_nutrition.json"
    return Settings(
        mcp_server_name="test-fitness-mcp",
        mcp_transport="stdio",
        open_wearables_api_url="https://test-wearables.local",
        open_wearables_api_key=SecretStr("mock-wearables-key-12345"),
        open_wearables_default_user_id="user-uuid-default-1",
        open_wearables_timeout=5.0,
        hevy_api_url="https://test-hevy.local/v1",
        hevy_api_key=SecretStr("mock-hevy-key-99999"),
        hevy_timeout=5.0,
        nutrition_provider="manual",
        nutrition_data_path=str(data_file),
        request_timeout=5.0,
        max_retries=2,
        backoff_factor=0.01,
    )


@pytest.fixture
def sample_activity_response() -> dict[str, Any]:
    """Sample raw payload returned by Open Wearables activity summary."""
    return {
        "records": [
            {
                "date": "2026-11-08",
                "steps": 10542,
                "distance_meters": 7800.0,
                "active_calories_kcal": 480.0,
                "total_calories_kcal": 2350.0,
                "active_minutes": 75,
                "heart_rate": {
                    "resting_bpm": 52,
                    "avg_bpm": 74,
                    "min_bpm": 48,
                    "max_bpm": 158,
                },
                "intensity_minutes": {
                    "light": 45,
                    "moderate": 20,
                    "vigorous": 10,
                },
            },
            {
                "date": "2026-11-09",
                "steps": 8400,
                "distance_meters": 6100.0,
                "active_calories_kcal": 360.0,
                "total_calories_kcal": 2180.0,
                "active_minutes": 50,
                "heart_rate": {
                    "resting_bpm": 54,
                    "avg_bpm": 71,
                    "min_bpm": 49,
                    "max_bpm": 142,
                },
                "intensity_minutes": {
                    "light": 35,
                    "moderate": 15,
                    "vigorous": 0,
                },
            },
        ]
    }


@pytest.fixture
def sample_sleep_response() -> dict[str, Any]:
    """Sample raw payload returned by Open Wearables sleep summary."""
    return {
        "records": [
            {
                "id": "sleep-session-1",
                "date": "2026-11-08",
                "start_time": "2026-11-07T23:15:00Z",
                "end_time": "2026-11-08T07:15:00Z",
                "total_sleep_seconds": 27000,  # 7.5 hours
                "time_in_bed_seconds": 28800,
                "efficiency_percent": 93.5,
                "stages": {
                    "deep_seconds": 5400,  # 1.5h
                    "rem_seconds": 6300,  # 1.75h
                    "light_seconds": 15300,
                    "awake_seconds": 1800,
                },
                "resting_heart_rate": 51,
                "hrv_sdnn": 64.5,
                "hrv_rmssd": 52.0,
                "sleep_score": 88,
            },
            {
                "id": "sleep-session-2",
                "date": "2026-11-09",
                "start_time": "2026-11-08T23:30:00Z",
                "end_time": "2026-11-09T07:00:00Z",
                "total_sleep_seconds": 25200,  # 7.0 hours
                "time_in_bed_seconds": 27000,
                "efficiency_percent": 90.0,
                "stages": {
                    "deep_seconds": 4500,
                    "rem_seconds": 5400,
                    "light_seconds": 15300,
                    "awake_seconds": 1800,
                },
                "resting_heart_rate": 53,
                "hrv_sdnn": 59.0,
                "hrv_rmssd": 48.0,
                "sleep_score": 82,
            },
        ]
    }


@pytest.fixture
def sample_hevy_workouts_response() -> dict[str, Any]:
    """Sample raw payload from Hevy workouts API."""
    return {
        "page": 1,
        "page_count": 1,
        "workouts": [
            {
                "id": "hevy-workout-101",
                "title": "Upper Body Strength (A)",
                "description": "Chest and Triceps focus",
                "start_time": "2026-11-09T17:00:00Z",
                "end_time": "2026-11-09T18:15:00Z",
                "exercises": [
                    {
                        "id": "ex-1",
                        "title": "Barbell Bench Press",
                        "exercise_template_id": "D04AC939",
                        "notes": "Solid bar path",
                        "sets": [
                            {
                                "index": 0,
                                "type": "warmup",
                                "weight_kg": 60.0,
                                "reps": 12,
                                "rpe": None,
                            },
                            {
                                "index": 1,
                                "type": "normal",
                                "weight_kg": 100.0,
                                "reps": 8,
                                "rpe": 8.0,
                            },
                            {
                                "index": 2,
                                "type": "normal",
                                "weight_kg": 100.0,
                                "reps": 7,
                                "rpe": 8.5,
                            },
                            {
                                "index": 3,
                                "type": "failure",
                                "weight_kg": 95.0,
                                "reps": 8,
                                "rpe": 10.0,
                            },
                        ],
                    },
                    {
                        "id": "ex-2",
                        "title": "Incline Dumbbell Press",
                        "exercise_template_id": "INC_DB_01",
                        "notes": None,
                        "sets": [
                            {
                                "index": 0,
                                "type": "normal",
                                "weight_kg": 36.0,
                                "reps": 10,
                                "rpe": 8.0,
                            },
                            {
                                "index": 1,
                                "type": "normal",
                                "weight_kg": 36.0,
                                "reps": 9,
                                "rpe": 8.5,
                            },
                        ],
                    },
                ],
            }
        ],
    }


@pytest.fixture
def wearables_client(mock_settings: Settings) -> OpenWearablesClient:
    return OpenWearablesClient(settings=mock_settings)


@pytest.fixture
def hevy_client(mock_settings: Settings) -> HevyClient:
    return HevyClient(settings=mock_settings)


@pytest.fixture
def nutrition_client(mock_settings: Settings) -> NutritionClient:
    return NutritionClient(settings=mock_settings)
