"""Client and adapter for Nutrition and macronutrient data (local persistence & extensible for MyFitnessPal)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fitness_hub.config import Settings, get_settings
from fitness_hub.models.nutrition import DailyNutritionSummary

logger = logging.getLogger(__name__)


class NutritionAdapter:
    """
    Nutrition client and storage adapter.
    Implements local JSON persistence with fallback and ready for MFP integration in Phase 2.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        self.provider = cfg.nutrition_provider
        self.data_path = Path(cfg.nutrition_data_path)
        self.target_calories = cfg.target_daily_calories
        self.target_protein_g = cfg.target_protein_g
        self._memory_store: dict[str, DailyNutritionSummary] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load records from local JSON file if it exists."""
        if not self.data_path.exists():
            return
        try:
            with open(self.data_path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            for date_str, record in data.items():
                self._memory_store[date_str] = DailyNutritionSummary.model_validate(record)
            logger.debug(
                "Loaded %d nutrition records from %s", len(self._memory_store), self.data_path
            )
        except Exception as e:
            logger.warning("Could not read nutrition data from %s: %s", self.data_path, e)

    def _save_to_disk(self) -> None:
        """Persist current memory store to JSON file."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {d: rec.model_dump() for d, rec in self._memory_store.items()}
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.error("Failed to persist nutrition data to %s: %s", self.data_path, e)

    async def get_daily_summary(self, date: str) -> DailyNutritionSummary:
        """
        Return DailyNutritionSummary for the specified date.
        If no entry exists yet, returns initialized summary against configured targets.
        """
        if date in self._memory_store:
            return self._memory_store[date]

        # Default fallback entry
        return DailyNutritionSummary(
            date=date,
            calories_kcal=0,
            protein_g=0,
            carbs_g=0,
            fat_g=0,
            target_calories=self.target_calories,
            target_protein_g=self.target_protein_g,
        )

    async def log_nutrition(
        self,
        date: str,
        calories_kcal: int,
        protein_g: int,
        carbs_g: int = 0,
        fat_g: int = 0,
    ) -> DailyNutritionSummary:
        """Log or update nutritional intake for a specific date."""
        summary = DailyNutritionSummary(
            date=date,
            calories_kcal=calories_kcal,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            target_calories=self.target_calories,
            target_protein_g=self.target_protein_g,
        )
        self._memory_store[date] = summary
        self._save_to_disk()
        return summary
