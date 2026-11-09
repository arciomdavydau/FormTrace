"""Unit tests for composite readiness, energy balance, and recovery-workload analytics tools."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from src.clients.hevy import HevyClient
from src.clients.nutrition import NutritionClient
from src.clients.wearables import OpenWearablesClient
from src.tools.biometrics_tools import set_wearables_client
from src.tools.composite_tools import (
    analyze_recovery_vs_workload,
    calculate_energy_balance,
    calculate_readiness_score,
)
from src.tools.nutrition_tools import set_nutrition_client
from src.tools.workout_tools import set_hevy_client


@pytest.fixture(autouse=True)
def setup_composite_clients(
    wearables_client: OpenWearablesClient,
    hevy_client: HevyClient,
    nutrition_client: NutritionClient,
) -> Any:
    set_wearables_client(wearables_client)
    set_hevy_client(hevy_client)
    set_nutrition_client(nutrition_client)
    yield
    set_wearables_client(None)
    set_hevy_client(None)
    set_nutrition_client(None)


@pytest.mark.asyncio
@respx.mock
async def test_calculate_readiness_score_optimal(
    sample_sleep_response: dict[str, Any],
    sample_hevy_workouts_response: dict[str, Any],
) -> None:
    """Test readiness score when sleep and recovery metrics are high."""
    # Mock sleep endpoint
    respx.get("https://test-wearables.local/api/v1/users/user-uuid-default-1/summaries/sleep").mock(
        return_value=httpx.Response(200, json=sample_sleep_response)
    )
    # Mock workouts endpoint
    respx.get("https://test-hevy.local/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_response)
    )

    result = await calculate_readiness_score(target_date="2026-11-09")

    assert "readiness_score" in result
    assert 0.0 <= result["readiness_score"] <= 100.0
    assert result["category"] in ["Optimal", "Good", "Moderate", "Low / Recovery Advised"]
    assert "components" in result
    assert result["components"]["sleep_duration_hours"] == 7.0
    assert result["components"]["resting_heart_rate"] == 53
    assert "recommendation" in result


@pytest.mark.asyncio
@respx.mock
async def test_calculate_energy_balance(
    sample_activity_response: dict[str, Any],
    nutrition_client: NutritionClient,
) -> None:
    """Test energy deficit calculation comparing wearable TDEE with food intake."""
    respx.get(
        "https://test-wearables.local/api/v1/users/user-uuid-default-1/summaries/activity"
    ).mock(
        return_value=httpx.Response(200, json={"records": [sample_activity_response["records"][0]]})
    )

    # 2026-11-08 TDEE was 2350.0 kcal.
    # Log 1850 kcal intake (a 500 kcal deficit)
    await nutrition_client.log_daily_summary(
        date="2026-11-08",
        calories=1850.0,
        protein_g=150.0,
        fat_g=60.0,
        carbs_g=180.0,
    )

    balance = await calculate_energy_balance(date="2026-11-08")

    assert balance["date"] == "2026-11-08"
    assert balance["energy_status"] == "Deficit"
    assert balance["intake_calories_kcal"] == 1850.0
    assert balance["expenditure_calories_kcal"] == 2350.0
    assert balance["net_balance_kcal"] == -500.0
    assert balance["net_percentage"] == round((-500.0 / 2350.0) * 100, 1)
    assert balance["activity_metrics"]["wearable_data_synced"] is True


@pytest.mark.asyncio
@respx.mock
async def test_analyze_recovery_vs_workload(
    sample_sleep_response: dict[str, Any],
    sample_hevy_workouts_response: dict[str, Any],
) -> None:
    """Test workload vs recovery synthesis."""
    respx.get("https://test-wearables.local/api/v1/users/user-uuid-default-1/summaries/sleep").mock(
        return_value=httpx.Response(200, json=sample_sleep_response)
    )
    respx.get("https://test-hevy.local/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_response)
    )

    analysis = await analyze_recovery_vs_workload(days=7)

    assert analysis["workload_metrics"]["workouts_completed"] == 1
    assert analysis["workload_metrics"]["total_tonnage_kg"] == 2944.0
    assert analysis["recovery_metrics"]["avg_sleep_hours"] == 7.25
    assert "workload_recovery_status" in analysis["synthesis"]
    assert "assessment" in analysis["synthesis"]
