"""Unit tests for NutritionClient adapter, file persistence, and macronutrient calculations."""

from __future__ import annotations

import pytest

from src.clients.base import FitnessMCPError
from src.clients.nutrition import NutritionClient
from src.config import Settings


@pytest.mark.asyncio
async def test_nutrition_empty_log(nutrition_client: NutritionClient) -> None:
    """Empty log for unrecorded day returns zero calories and clean targets."""
    log = await nutrition_client.get_daily_log("2026-11-09")
    assert log.date == "2026-11-09"
    assert log.total_calories == 0.0
    assert log.total_protein_g == 0.0
    assert len(log.meals) == 0


@pytest.mark.asyncio
async def test_nutrition_log_food_and_meals(nutrition_client: NutritionClient) -> None:
    """Log individual food items across meals and verify totals and net carbs."""
    # Breakfast: 2 Eggs + Oats
    await nutrition_client.log_food(
        date="2026-11-09",
        meal="Breakfast",
        food_name="Whole Eggs (2)",
        calories=140.0,
        protein_g=12.0,
        carbs_g=1.0,
        fat_g=10.0,
        fiber_g=0.0,
    )
    await nutrition_client.log_food(
        date="2026-11-09",
        meal="Breakfast",
        food_name="Rolled Oats (50g)",
        calories=185.0,
        protein_g=6.5,
        carbs_g=33.0,
        fat_g=3.0,
        fiber_g=5.0,
    )

    # Lunch: Chicken breast + Rice
    await nutrition_client.log_food(
        date="2026-11-09",
        meal="Lunch",
        food_name="Grilled Chicken Breast (200g)",
        calories=330.0,
        protein_g=62.0,
        carbs_g=0.0,
        fat_g=7.2,
    )

    daily = await nutrition_client.get_daily_log("2026-11-09")
    assert len(daily.meals) == 2
    # 140 + 185 + 330 = 655 kcal
    assert daily.total_calories == 655.0
    # 12 + 6.5 + 62 = 80.5 g protein
    assert daily.total_protein_g == 80.5
    # 1 + 33 = 34 g carbs
    assert daily.total_carbs_g == 34.0
    # 10 + 3 + 7.2 = 20.2 g fat
    assert daily.total_fat_g == 20.2
    # 5.0 g fiber
    assert daily.total_fiber_g == 5.0
    # Net carbs = 34 - 5 = 29 g
    assert daily.net_carbs_g == 29.0


@pytest.mark.asyncio
async def test_nutrition_direct_macros_and_water(nutrition_client: NutritionClient) -> None:
    """Test fast summary logging without itemizing meals."""
    await nutrition_client.log_daily_summary(
        date="2026-11-08",
        calories=2200.0,
        protein_g=160.0,
        fat_g=70.0,
        carbs_g=230.0,
        fiber_g=30.0,
        water_ml=2500.0,
    )

    daily = await nutrition_client.get_daily_log("2026-11-08")
    assert daily.total_calories == 2200.0
    assert daily.total_protein_g == 160.0
    assert daily.total_fat_g == 70.0
    assert daily.total_carbs_g == 230.0
    assert daily.total_fiber_g == 30.0
    assert daily.water_ml == 2500.0


@pytest.mark.asyncio
async def test_nutrition_targets_and_persistence(mock_settings: Settings) -> None:
    """Test setting targets and reloading from disk."""
    client1 = NutritionClient(settings=mock_settings)
    await client1.set_macro_targets(
        calories=2400.0,
        protein_g=180.0,
        fat_g=75.0,
        carbs_g=250.0,
    )
    await client1.log_daily_summary(
        date="2026-11-05",
        calories=2350.0,
        protein_g=175.0,
        fat_g=70.0,
        carbs_g=240.0,
    )

    # Initialize a new client with the same data file to test persistence
    client2 = NutritionClient(settings=mock_settings)
    targets = await client2.get_macro_targets()
    assert targets is not None
    assert targets.calories == 2400.0
    assert targets.protein_g == 180.0

    log = await client2.get_daily_log("2026-11-05")
    assert log.total_calories == 2350.0
    assert log.total_protein_g == 175.0


@pytest.mark.asyncio
async def test_nutrition_validation_error(nutrition_client: NutritionClient) -> None:
    """Negative values should raise FitnessMCPError."""
    with pytest.raises(FitnessMCPError):
        await nutrition_client.log_daily_summary(
            date="2026-11-09",
            calories=-500.0,
            protein_g=50.0,
            fat_g=20.0,
            carbs_g=50.0,
        )
