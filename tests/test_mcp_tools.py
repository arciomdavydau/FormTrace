"""Unit tests for individual domain MCP tools."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from src.clients.hevy import HevyClient
from src.clients.nutrition import NutritionClient
from src.clients.wearables import OpenWearablesClient
from src.tools.biometrics_tools import (
    get_daily_activity,
    get_sleep_data,
    set_wearables_client,
)
from src.tools.nutrition_tools import (
    get_daily_nutrition,
    log_food_entry,
    set_macro_goals,
    set_nutrition_client,
)
from src.tools.workout_tools import (
    get_recent_workouts,
    get_workout_details,
    get_workout_volume_analytics,
    set_hevy_client,
)


@pytest.fixture(autouse=True)
def setup_tool_clients(
    wearables_client: OpenWearablesClient,
    hevy_client: HevyClient,
    nutrition_client: NutritionClient,
) -> Any:
    """Inject mock clients into tool modules before running each test."""
    set_wearables_client(wearables_client)
    set_hevy_client(hevy_client)
    set_nutrition_client(nutrition_client)
    yield
    set_wearables_client(None)
    set_hevy_client(None)
    set_nutrition_client(None)


@pytest.mark.asyncio
@respx.mock
async def test_tool_daily_activity(sample_activity_response: dict[str, Any]) -> None:
    """Test get_daily_activity tool."""
    respx.get(
        "https://test-wearables.local/api/v1/users/user-uuid-default-1/summaries/activity"
    ).mock(return_value=httpx.Response(200, json=sample_activity_response))

    res = await get_daily_activity("2026-11-08", "2026-11-09")
    assert res["days_count"] == 2
    assert res["total_steps"] == 18942
    assert res["avg_daily_steps"] == 9471.0
    assert len(res["records"]) == 2


@pytest.mark.asyncio
@respx.mock
async def test_tool_sleep_data(sample_sleep_response: dict[str, Any]) -> None:
    """Test get_sleep_data tool."""
    respx.get("https://test-wearables.local/api/v1/users/user-uuid-default-1/summaries/sleep").mock(
        return_value=httpx.Response(200, json=sample_sleep_response)
    )

    res = await get_sleep_data("2026-11-08", "2026-11-09")
    assert res["total_sessions"] == 2
    assert res["avg_sleep_hours"] == 7.25
    assert res["avg_efficiency_percent"] == 91.8
    assert len(res["sessions"]) == 2


@pytest.mark.asyncio
@respx.mock
async def test_tool_recent_workouts(sample_hevy_workouts_response: dict[str, Any]) -> None:
    """Test get_recent_workouts tool."""
    respx.get("https://test-hevy.local/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_response)
    )

    res = await get_recent_workouts(page=1, page_size=5)
    assert res["count"] == 1
    w = res["workouts"][0]
    assert w["title"] == "Upper Body Strength (A)"
    assert w["total_tonnage_kg"] == 2944.0
    assert w["working_sets_count"] == 5
    assert "Barbell Bench Press" in w["exercise_titles"]


@pytest.mark.asyncio
@respx.mock
async def test_tool_workout_details(sample_hevy_workouts_response: dict[str, Any]) -> None:
    """Test get_workout_details tool."""
    respx.get("https://test-hevy.local/v1/workouts/hevy-workout-101").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_response["workouts"][0])
    )

    res = await get_workout_details("hevy-workout-101")
    assert res["id"] == "hevy-workout-101"
    assert res["total_tonnage_kg"] == 2944.0
    assert len(res["exercises"]) == 2
    assert res["exercises"][0]["title"] == "Barbell Bench Press"
    assert res["exercises"][0]["total_volume_kg"] == 2260.0


@pytest.mark.asyncio
@respx.mock
async def test_tool_workout_volume_analytics(sample_hevy_workouts_response: dict[str, Any]) -> None:
    """Test get_workout_volume_analytics tool."""
    respx.get("https://test-hevy.local/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_response)
    )

    res = await get_workout_volume_analytics()
    assert res["total_workouts_analyzed"] == 1
    assert res["total_tonnage_kg"] == 2944.0
    assert res["max_weights_kg"]["Barbell Bench Press"] == 100.0


@pytest.mark.asyncio
async def test_tool_nutrition_workflow() -> None:
    """Test setting goals, logging food, and querying daily nutrition."""
    # Set targets
    await set_macro_goals(calories=2200.0, protein_g=160.0, fat_g=70.0, carbs_g=230.0)

    # Log food
    await log_food_entry(
        date="2026-11-09",
        meal="Lunch",
        food_name="Steak & Sweet Potato",
        calories=750.0,
        protein_g=60.0,
        carbs_g=55.0,
        fat_g=28.0,
        fiber_g=8.0,
    )

    # Query daily log
    res = await get_daily_nutrition("2026-11-09")
    assert res["total_calories"] == 750.0
    assert res["total_protein_g"] == 60.0
    assert res["vs_targets"]["target_calories"] == 2200.0
    assert res["vs_targets"]["calories_diff"] == -1450.0  # 750 - 2200
