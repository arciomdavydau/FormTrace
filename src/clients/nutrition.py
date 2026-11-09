"""Nutrition adapter providing daily macronutrient and food intake management."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.clients.base import FitnessMCPError
from src.config import Settings, get_settings
from src.models.nutrition import (
    DailyFoodLog,
    FoodItem,
    MacroSummary,
    MacroTargets,
    MealLog,
)

logger = logging.getLogger(__name__)


class NutritionClient:
    """
    Nutrition client adapter supporting manual tracking with JSON persistence
    and MyFitnessPal compatibility.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        self.provider = cfg.nutrition_provider
        self.data_path = Path(cfg.nutrition_data_path)
        self.mfp_username = cfg.myfitnesspal_username
        self.mfp_password = (
            cfg.myfitnesspal_password.get_secret_value() if cfg.myfitnesspal_password else None
        )

        self._logs: dict[str, DailyFoodLog] = {}
        self._targets: MacroTargets | None = None
        self._load_local_data()

    def _load_local_data(self) -> None:
        """Load persisted nutrition records from disk if available."""
        if not self.data_path.exists():
            return
        try:
            with open(self.data_path, encoding="utf-8") as f:
                raw_data = json.load(f)

            targets_raw = raw_data.get("targets")
            if targets_raw:
                self._targets = MacroTargets.model_validate(targets_raw)

            for date_str, log_dict in raw_data.get("logs", {}).items():
                self._logs[date_str] = DailyFoodLog.model_validate(log_dict)

            logger.info(
                "Loaded nutrition data with %d days from %s", len(self._logs), self.data_path
            )
        except Exception as e:
            logger.warning("Could not load existing nutrition data from %s: %s", self.data_path, e)

    def _save_local_data(self) -> None:
        """Persist current nutrition logs to disk."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            serializable_logs = {k: v.model_dump() for k, v in self._logs.items()}
            data = {
                "targets": self._targets.model_dump() if self._targets else None,
                "logs": serializable_logs,
            }
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save nutrition data to %s: %s", self.data_path, e)

    async def get_daily_log(self, date: str) -> DailyFoodLog:
        """
        Retrieve food and macro logs for a given date (YYYY-MM-DD).
        If no log exists yet, an empty initialized log is returned.
        """
        if date in self._logs:
            log = self._logs[date]
            if not log.targets and self._targets:
                log.targets = self._targets
            return log

        empty_log = DailyFoodLog(date=date, targets=self._targets)
        return empty_log

    async def log_food(
        self,
        date: str,
        meal: str,
        food_name: str,
        calories: float,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
        fiber_g: float = 0.0,
        serving_size: str | None = None,
    ) -> DailyFoodLog:
        """Add an individual food item to a specific meal."""
        if calories < 0 or protein_g < 0 or carbs_g < 0 or fat_g < 0 or fiber_g < 0:
            raise FitnessMCPError("Nutritional values cannot be negative")

        item = FoodItem(
            name=food_name,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            fiber_g=fiber_g,
            serving_size=serving_size,
        )

        daily = await self.get_daily_log(date)

        # Find existing meal or create new
        target_meal: MealLog | None = None
        for m in daily.meals:
            if m.meal_name.strip().lower() == meal.strip().lower():
                target_meal = m
                break

        if target_meal is None:
            target_meal = MealLog(meal_name=meal.capitalize(), items=[item])
            daily.meals.append(target_meal)
        else:
            target_meal.items.append(item)

        # Clear direct override if itemized logging is used
        daily.direct_calories = None
        daily.direct_protein_g = None
        daily.direct_fat_g = None
        daily.direct_carbs_g = None
        daily.direct_fiber_g = None

        self._logs[date] = daily
        self._save_local_data()
        return daily

    async def log_daily_summary(
        self,
        date: str,
        calories: float,
        protein_g: float,
        fat_g: float,
        carbs_g: float,
        fiber_g: float = 0.0,
        water_ml: float | None = None,
    ) -> DailyFoodLog:
        """
        Record a direct aggregate daily summary of calories and macros.
        Useful when meals aren't itemized one by one.
        """
        if calories < 0 or protein_g < 0 or fat_g < 0 or carbs_g < 0 or fiber_g < 0:
            raise FitnessMCPError("Macro values cannot be negative")

        daily = await self.get_daily_log(date)
        daily.direct_calories = calories
        daily.direct_protein_g = protein_g
        daily.direct_fat_g = fat_g
        daily.direct_carbs_g = carbs_g
        daily.direct_fiber_g = fiber_g
        if water_ml is not None:
            daily.water_ml = water_ml

        self._logs[date] = daily
        self._save_local_data()
        return daily

    async def set_macro_targets(
        self,
        calories: float,
        protein_g: float,
        fat_g: float,
        carbs_g: float,
    ) -> MacroTargets:
        """Configure user daily calorie and macronutrient targets."""
        if calories <= 0 or protein_g < 0 or fat_g < 0 or carbs_g < 0:
            raise FitnessMCPError("Targets must be positive numbers")

        targets = MacroTargets(
            calories=calories,
            protein_g=protein_g,
            fat_g=fat_g,
            carbs_g=carbs_g,
        )
        self._targets = targets
        self._save_local_data()
        return targets

    async def get_macro_targets(self) -> MacroTargets | None:
        """Return configured daily macronutrient goals."""
        return self._targets

    async def get_macro_summary(self, start_date: str, end_date: str) -> MacroSummary:
        """
        Calculate daily averages and adherence over a given date period (YYYY-MM-DD).
        """
        matched_logs: list[DailyFoodLog] = []
        for date_str, log in sorted(self._logs.items()):
            if start_date <= date_str <= end_date and log.total_calories > 0:
                matched_logs.append(log)

        days_count = len(matched_logs)
        if days_count == 0:
            return MacroSummary(
                start_date=start_date,
                end_date=end_date,
                days_tracked=0,
                avg_daily_calories=0.0,
                avg_daily_protein_g=0.0,
                avg_daily_fat_g=0.0,
                avg_daily_carbs_g=0.0,
                avg_daily_fiber_g=0.0,
                daily_logs=[],
            )

        avg_cals = sum(log.total_calories for log in matched_logs) / days_count
        avg_prot = sum(log.total_protein_g for log in matched_logs) / days_count
        avg_fat = sum(log.total_fat_g for log in matched_logs) / days_count
        avg_carbs = sum(log.total_carbs_g for log in matched_logs) / days_count
        avg_fiber = sum(log.total_fiber_g for log in matched_logs) / days_count

        return MacroSummary(
            start_date=start_date,
            end_date=end_date,
            days_tracked=days_count,
            avg_daily_calories=round(avg_cals, 1),
            avg_daily_protein_g=round(avg_prot, 1),
            avg_daily_fat_g=round(avg_fat, 1),
            avg_daily_carbs_g=round(avg_carbs, 1),
            avg_daily_fiber_g=round(avg_fiber, 1),
            daily_logs=matched_logs,
        )
