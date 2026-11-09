"""Tests for FitnessAggregatorService readiness scoring engine, parallel fetching, and coaching flags."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from fitness_hub.clients.hevy import HevyClient
from fitness_hub.clients.nutrition import NutritionAdapter
from fitness_hub.clients.wearables import WearablesClient
from fitness_hub.config import Settings
from fitness_hub.server import create_server, set_aggregator_service
from fitness_hub.services.aggregator import FitnessAggregatorService


@pytest.mark.asyncio
@respx.mock
async def test_readiness_engine_optimal_state(
    mock_settings: Settings,
    sample_wearables_activity_payload: dict[str, Any],
    sample_wearables_sleep_payload: dict[str, Any],
    sample_hevy_workouts_payload: dict[str, Any],
) -> None:
    """Verify optimal recovery when sleep is sufficient, HR is low, and protein goal is met."""
    wearables = WearablesClient(settings=mock_settings)
    hevy = HevyClient(settings=mock_settings)
    nutrition = NutritionAdapter(settings=mock_settings)

    # Pre-seed protein goal adherence for previous day
    await nutrition.log_nutrition(
        date="2026-11-08",
        calories_kcal=2300,
        protein_g=195,  # Met (target is 180g)
        carbs_g=240,
        fat_g=70,
    )

    # Mock upstreams
    respx.get("http://localhost:8080/api/v1/activity/2026-11-09").mock(
        return_value=httpx.Response(200, json=sample_wearables_activity_payload)
    )
    respx.get("http://localhost:8080/api/v1/sleep/2026-11-09").mock(
        return_value=httpx.Response(200, json=sample_wearables_sleep_payload)
    )
    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_payload)
    )

    service = FitnessAggregatorService(
        wearables_client=wearables,
        hevy_client=hevy,
        nutrition_adapter=nutrition,
        settings=mock_settings,
    )

    report = await service.generate_readiness_report("2026-11-09")

    assert report.date == "2026-11-09"
    assert report.readiness_score >= 80
    assert report.status == "OPTIMAL"
    assert report.biometrics is not None
    assert report.biometrics.sleep is not None
    assert report.biometrics.sleep.total_sleep_minutes == 465
    assert report.last_workout is not None
    assert report.last_workout.working_tonnage_kg == 5400.0

    # Coaching notes check
    assert any("Sleep duration target met" in note for note in report.coaching_notes)
    assert any("Protein goal achieved" in note for note in report.coaching_notes)


@pytest.mark.asyncio
@respx.mock
async def test_readiness_engine_recovery_needed_state(
    mock_settings: Settings,
    sample_hevy_workouts_payload: dict[str, Any],
) -> None:
    """Verify recovery needed status when sleep is short, resting HR is elevated, and prior tonnage is huge."""
    wearables = WearablesClient(settings=mock_settings)
    hevy = HevyClient(settings=mock_settings)
    nutrition = NutritionAdapter(settings=mock_settings)

    # Poor nutrition on previous day (low protein)
    await nutrition.log_nutrition(
        date="2026-11-08",
        calories_kcal=1400,
        protein_g=90,  # Far below target 180g
        carbs_g=150,
        fat_g=45,
    )

    # Short sleep payload (<6.5h) and elevated resting HR (>65 bpm)
    poor_sleep_payload = {
        "date": "2026-11-09",
        "total_sleep_minutes": 310,  # 5.16 hours (< 390 min)
        "deep_sleep_minutes": 40,
        "rem_sleep_minutes": 45,
        "sleep_efficiency_pct": 74.0,
        "resting_hr_bpm": 72,  # Elevated > 65 bpm
    }
    poor_activity_payload = {
        "date": "2026-11-09",
        "steps": 3200,
        "active_calories": 150,
        "resting_hr_bpm": 72,
    }

    # High volume Hevy session (>8,000 kg tonnage)
    heavy_squats = [
        {
            "type": "normal",
            "weight_kg": 160.0,
            "reps": 10,
            "rpe": 9.5,
        }  # 1600 kg per set x 6 = 9600 kg
        for _ in range(6)
    ]
    high_volume_workout_payload = {
        "workouts": [
            {
                "id": "heavy-tonnage-session",
                "title": "Brutal Squat Day",
                "start_time": "2026-11-08T20:00:00Z",
                "exercises": [
                    {
                        "title": "Barbell Squat",
                        "sets": heavy_squats,
                    }
                ],
            }
        ]
    }

    respx.get("http://localhost:8080/api/v1/activity/2026-11-09").mock(
        return_value=httpx.Response(200, json=poor_activity_payload)
    )
    respx.get("http://localhost:8080/api/v1/sleep/2026-11-09").mock(
        return_value=httpx.Response(200, json=poor_sleep_payload)
    )
    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json=high_volume_workout_payload)
    )

    service = FitnessAggregatorService(
        wearables_client=wearables,
        hevy_client=hevy,
        nutrition_adapter=nutrition,
        settings=mock_settings,
    )

    report = await service.generate_readiness_report("2026-11-09")

    assert report.readiness_score < 60
    assert report.status == "RECOVERY_NEEDED"

    notes = " ".join(report.coaching_notes)
    assert "Sub-optimal sleep (<6.5h)" in notes
    assert "Elevated resting heart rate detected (>5 bpm above baseline)" in notes
    assert "High central nervous system load from previous workout" in notes
    assert "Low protein intake (< 180g)" in notes


@pytest.mark.asyncio
@respx.mock
async def test_fastmcp_server_tools_end_to_end(
    mock_settings: Settings,
    sample_wearables_activity_payload: dict[str, Any],
    sample_wearables_sleep_payload: dict[str, Any],
    sample_hevy_workouts_payload: dict[str, Any],
) -> None:
    """Test all 4 FastMCP gateway tools registered on server."""
    wearables = WearablesClient(settings=mock_settings)
    hevy = HevyClient(settings=mock_settings)
    nutrition = NutritionAdapter(settings=mock_settings)

    await nutrition.log_nutrition("2026-11-09", calories_kcal=2100, protein_g=185)

    respx.get("http://localhost:8080/api/v1/activity/2026-11-09").mock(
        return_value=httpx.Response(200, json=sample_wearables_activity_payload)
    )
    respx.get("http://localhost:8080/api/v1/sleep/2026-11-09").mock(
        return_value=httpx.Response(200, json=sample_wearables_sleep_payload)
    )
    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_payload)
    )

    service = FitnessAggregatorService(
        wearables_client=wearables,
        hevy_client=hevy,
        nutrition_adapter=nutrition,
        settings=mock_settings,
    )
    set_aggregator_service(service)

    server = create_server()

    # 1. get_daily_biometrics
    biometrics_res = await server.call_tool("get_daily_biometrics", {"target_date": "2026-11-09"})
    # fastmcp returns tool call result
    assert biometrics_res is not None

    # 2. get_recent_strength_workouts
    workouts_res = await server.call_tool("get_recent_strength_workouts", {"limit": 2})
    assert workouts_res is not None

    # 3. get_nutrition_status
    nutrition_res = await server.call_tool("get_nutrition_status", {"target_date": "2026-11-09"})
    assert nutrition_res is not None

    # 4. get_comprehensive_readiness_report
    readiness_res = await server.call_tool(
        "get_comprehensive_readiness_report", {"target_date": "2026-11-09"}
    )
    assert readiness_res is not None
