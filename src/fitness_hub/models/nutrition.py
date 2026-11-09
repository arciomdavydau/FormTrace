"""Domain models for daily nutrition, macronutrients, and adherence math."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MacroTargets(BaseModel):
    """Macronutrient and caloric goals."""

    model_config = ConfigDict(extra="ignore")

    calories: int = Field(gt=0, description="Target daily energy in kcal")
    protein_g: int = Field(ge=0, description="Target daily protein in grams")
    carbs_g: int | None = Field(default=None, ge=0, description="Target daily carbs in grams")
    fat_g: int | None = Field(default=None, ge=0, description="Target daily fats in grams")


class DailyNutritionSummary(BaseModel):
    """Summary of daily nutritional intake compared against target goals."""

    model_config = ConfigDict(extra="ignore")

    date: str = Field(description="Record date (YYYY-MM-DD)")
    calories_kcal: int = Field(ge=0, description="Total caloric intake in kcal")
    protein_g: int = Field(ge=0, description="Protein consumed in grams")
    carbs_g: int = Field(default=0, ge=0, description="Carbohydrates consumed in grams")
    fat_g: int = Field(default=0, ge=0, description="Fats consumed in grams")
    target_calories: int = Field(default=2200, gt=0, description="Target daily calories")
    target_protein_g: int = Field(default=180, ge=0, description="Target daily protein in grams")

    @property
    def calorie_delta(self) -> int:
        """Net difference between consumed calories and target (negative = deficit)."""
        return self.calories_kcal - self.target_calories

    @property
    def protein_goal_met(self) -> bool:
        """Whether the consumed protein meets or exceeds the target."""
        return self.protein_g >= self.target_protein_g
