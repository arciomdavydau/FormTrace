"""MCP tools for food logging, daily macros, caloric targets, and nutrient analytics."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from src.clients.nutrition import NutritionClient

logger = logging.getLogger(__name__)

nutrition_router = FastMCP(name="Nutrition Tools")
_client: NutritionClient | None = None


def get_nutrition_client() -> NutritionClient:
    """Get or instantiate singleton NutritionClient."""
    global _client
    if _client is None:
        _client = NutritionClient()
    return _client


def set_nutrition_client(client: NutritionClient | None) -> None:
    """Override client for testing/injection."""
    global _client
    _client = client


@nutrition_router.tool
async def get_daily_nutrition(date: str) -> dict[str, Any]:
    """
    Get nutritional intake (calories, protein, carbs, fat, fiber, meals) for a specific date (YYYY-MM-DD).

    Args:
        date: Target date in YYYY-MM-DD format (e.g. '2026-11-09')
    """
    client = get_nutrition_client()
    log = await client.get_daily_log(date)

    meals_summary = []
    for m in log.meals:
        meals_summary.append(
            {
                "meal": m.meal_name,
                "calories": m.total_calories,
                "protein_g": m.total_protein_g,
                "carbs_g": m.total_carbs_g,
                "fat_g": m.total_fat_g,
                "fiber_g": m.total_fiber_g,
                "items": [item.model_dump() for item in m.items],
            }
        )

    # Calculate caloric distribution
    tot_cal = log.total_calories
    protein_pct = round((log.total_protein_g * 4.0 / tot_cal) * 100, 1) if tot_cal > 0 else 0.0
    carbs_pct = round((log.total_carbs_g * 4.0 / tot_cal) * 100, 1) if tot_cal > 0 else 0.0
    fat_pct = round((log.total_fat_g * 9.0 / tot_cal) * 100, 1) if tot_cal > 0 else 0.0

    targets_diff = None
    if log.targets:
        targets_diff = {
            "target_calories": log.targets.calories,
            "calories_diff": round(log.total_calories - log.targets.calories, 1),
            "target_protein_g": log.targets.protein_g,
            "protein_diff": round(log.total_protein_g - log.targets.protein_g, 1),
            "target_fat_g": log.targets.fat_g,
            "fat_diff": round(log.total_fat_g - log.targets.fat_g, 1),
            "target_carbs_g": log.targets.carbs_g,
            "carbs_diff": round(log.total_carbs_g - log.targets.carbs_g, 1),
        }

    return {
        "date": log.date,
        "total_calories": log.total_calories,
        "total_protein_g": log.total_protein_g,
        "total_carbs_g": log.total_carbs_g,
        "total_fat_g": log.total_fat_g,
        "total_fiber_g": log.total_fiber_g,
        "net_carbs_g": log.net_carbs_g,
        "water_ml": log.water_ml,
        "macronutrient_distribution_pct": {
            "protein": protein_pct,
            "carbohydrates": carbs_pct,
            "fat": fat_pct,
        },
        "vs_targets": targets_diff,
        "meals": meals_summary,
    }


@nutrition_router.tool
async def get_nutrition_summary(start_date: str, end_date: str) -> dict[str, Any]:
    """
    Get aggregated macronutrient and caloric averages over a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    client = get_nutrition_client()
    summary = await client.get_macro_summary(start_date, end_date)

    tot_avg_cal = summary.avg_daily_calories
    protein_pct = (
        round((summary.avg_daily_protein_g * 4.0 / tot_avg_cal) * 100, 1)
        if tot_avg_cal > 0
        else 0.0
    )
    carbs_pct = (
        round((summary.avg_daily_carbs_g * 4.0 / tot_avg_cal) * 100, 1) if tot_avg_cal > 0 else 0.0
    )
    fat_pct = (
        round((summary.avg_daily_fat_g * 9.0 / tot_avg_cal) * 100, 1) if tot_avg_cal > 0 else 0.0
    )

    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "days_tracked": summary.days_tracked,
        "averages": {
            "daily_calories": summary.avg_daily_calories,
            "daily_protein_g": summary.avg_daily_protein_g,
            "daily_fat_g": summary.avg_daily_fat_g,
            "daily_carbs_g": summary.avg_daily_carbs_g,
            "daily_fiber_g": summary.avg_daily_fiber_g,
        },
        "macro_split_percentage": {
            "protein": protein_pct,
            "carbohydrates": carbs_pct,
            "fat": fat_pct,
        },
    }


@nutrition_router.tool
async def log_food_entry(
    date: str,
    meal: str,
    food_name: str,
    calories: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    fiber_g: float = 0.0,
    serving_size: str | None = None,
) -> dict[str, Any]:
    """
    Log an individual food item to a meal (e.g. Breakfast, Lunch, Dinner, Snack).

    Args:
        date: Date in YYYY-MM-DD format
        meal: Meal name (e.g. 'Breakfast', 'Post-Workout')
        food_name: Name of food item (e.g. 'Greek Yogurt 2%', 'Chicken Breast')
        calories: Energy in kcal
        protein_g: Protein in grams
        carbs_g: Carbohydrates in grams
        fat_g: Fat in grams
        fiber_g: Dietary fiber in grams (default: 0.0)
        serving_size: Optional description of serving size (e.g. '200g')
    """
    client = get_nutrition_client()
    updated = await client.log_food(
        date=date,
        meal=meal,
        food_name=food_name,
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        fiber_g=fiber_g,
        serving_size=serving_size,
    )
    return {
        "status": "success",
        "date": date,
        "logged_meal": meal,
        "daily_total_calories": updated.total_calories,
        "daily_total_protein_g": updated.total_protein_g,
        "daily_total_carbs_g": updated.total_carbs_g,
        "daily_total_fat_g": updated.total_fat_g,
    }


@nutrition_router.tool
async def log_daily_macros(
    date: str,
    calories: float,
    protein_g: float,
    fat_g: float,
    carbs_g: float,
    fiber_g: float = 0.0,
    water_ml: float | None = None,
) -> dict[str, Any]:
    """
    Record aggregated total daily macros without entering individual meals.

    Args:
        date: Date in YYYY-MM-DD format
        calories: Total daily calories in kcal
        protein_g: Total daily protein in grams
        fat_g: Total daily fat in grams
        carbs_g: Total daily carbs in grams
        fiber_g: Total daily fiber in grams
        water_ml: Total water intake in ml
    """
    client = get_nutrition_client()
    updated = await client.log_daily_summary(
        date=date,
        calories=calories,
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
        fiber_g=fiber_g,
        water_ml=water_ml,
    )
    return {
        "status": "success",
        "date": date,
        "daily_total_calories": updated.total_calories,
        "daily_total_protein_g": updated.total_protein_g,
        "daily_total_carbs_g": updated.total_carbs_g,
        "daily_total_fat_g": updated.total_fat_g,
        "water_ml": updated.water_ml,
    }


@nutrition_router.tool
async def set_macro_goals(
    calories: float,
    protein_g: float,
    fat_g: float,
    carbs_g: float,
) -> dict[str, Any]:
    """
    Set target daily calories and macronutrient breakdown.

    Args:
        calories: Daily target calories (kcal)
        protein_g: Target daily protein (grams)
        fat_g: Target daily fat (grams)
        carbs_g: Target daily carbohydrates (grams)
    """
    client = get_nutrition_client()
    targets = await client.set_macro_targets(
        calories=calories,
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
    )
    return {
        "status": "goals_updated",
        "target_calories": targets.calories,
        "target_protein_g": targets.protein_g,
        "target_fat_g": targets.fat_g,
        "target_carbs_g": targets.carbs_g,
    }
