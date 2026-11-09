"""Pydantic data models for nutrition tracking, macronutrients, and meal logging."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FoodItem(BaseModel):
    """An individual food item with nutritional values."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="Name or description of the food item")
    calories: float = Field(ge=0, description="Energy in kilocalories")
    protein_g: float = Field(ge=0, description="Protein in grams")
    carbs_g: float = Field(ge=0, description="Total carbohydrates in grams")
    fat_g: float = Field(ge=0, description="Total fats in grams")
    fiber_g: float = Field(default=0.0, ge=0, description="Dietary fiber in grams")
    serving_size: str | None = Field(
        default=None, description="Portion size (e.g. '100g', '1 scoop')"
    )


class MealLog(BaseModel):
    """A meal grouping (e.g. breakfast, lunch, post-workout)."""

    model_config = ConfigDict(extra="ignore")

    meal_name: str = Field(description="Name of the meal (e.g. 'Breakfast', 'Lunch', 'Snack')")
    items: list[FoodItem] = Field(default_factory=list, description="Food items consumed")

    @property
    def total_calories(self) -> float:
        return round(sum(item.calories for item in self.items), 1)

    @property
    def total_protein_g(self) -> float:
        return round(sum(item.protein_g for item in self.items), 1)

    @property
    def total_carbs_g(self) -> float:
        return round(sum(item.carbs_g for item in self.items), 1)

    @property
    def total_fat_g(self) -> float:
        return round(sum(item.fat_g for item in self.items), 1)

    @property
    def total_fiber_g(self) -> float:
        return round(sum(item.fiber_g for item in self.items), 1)


class MacroTargets(BaseModel):
    """Daily nutritional and macronutrient targets."""

    model_config = ConfigDict(extra="ignore")

    calories: float = Field(description="Target daily calories (kcal)")
    protein_g: float = Field(description="Target daily protein (g)")
    fat_g: float = Field(description="Target daily fat (g)")
    carbs_g: float = Field(description="Target daily carbohydrates (g)")


class DailyFoodLog(BaseModel):
    """Complete food and macronutrient log for a single day."""

    model_config = ConfigDict(extra="ignore")

    date: str = Field(description="Date for the log (YYYY-MM-DD)")
    meals: list[MealLog] = Field(default_factory=list, description="Logged meals for the day")
    water_ml: float | None = Field(default=None, description="Total water intake in milliliters")
    targets: MacroTargets | None = Field(default=None, description="Macronutrient goals")

    # In case user logged direct daily aggregates instead of meal items:
    direct_calories: float | None = Field(
        default=None, description="Directly recorded total calories"
    )
    direct_protein_g: float | None = Field(
        default=None, description="Directly recorded total protein (g)"
    )
    direct_fat_g: float | None = Field(default=None, description="Directly recorded total fat (g)")
    direct_carbs_g: float | None = Field(
        default=None, description="Directly recorded total carbs (g)"
    )
    direct_fiber_g: float | None = Field(
        default=None, description="Directly recorded total fiber (g)"
    )

    @property
    def total_calories(self) -> float:
        if self.direct_calories is not None:
            return round(self.direct_calories, 1)
        return round(sum(m.total_calories for m in self.meals), 1)

    @property
    def total_protein_g(self) -> float:
        if self.direct_protein_g is not None:
            return round(self.direct_protein_g, 1)
        return round(sum(m.total_protein_g for m in self.meals), 1)

    @property
    def total_carbs_g(self) -> float:
        if self.direct_carbs_g is not None:
            return round(self.direct_carbs_g, 1)
        return round(sum(m.total_carbs_g for m in self.meals), 1)

    @property
    def total_fat_g(self) -> float:
        if self.direct_fat_g is not None:
            return round(self.direct_fat_g, 1)
        return round(sum(m.total_fat_g for m in self.meals), 1)

    @property
    def total_fiber_g(self) -> float:
        if self.direct_fiber_g is not None:
            return round(self.direct_fiber_g, 1)
        return round(sum(m.total_fiber_g for m in self.meals), 1)

    @property
    def net_carbs_g(self) -> float:
        return max(0.0, round(self.total_carbs_g - self.total_fiber_g, 1))


class MacroSummary(BaseModel):
    """Macronutrient averages and intake metrics across a date range."""

    model_config = ConfigDict(extra="ignore")

    start_date: str = Field(description="Start date (YYYY-MM-DD)")
    end_date: str = Field(description="End date (YYYY-MM-DD)")
    days_tracked: int = Field(default=0, description="Number of days with logged nutrition")
    avg_daily_calories: float = Field(
        default=0.0, description="Average daily calorie intake (kcal)"
    )
    avg_daily_protein_g: float = Field(default=0.0, description="Average daily protein intake (g)")
    avg_daily_fat_g: float = Field(default=0.0, description="Average daily fat intake (g)")
    avg_daily_carbs_g: float = Field(
        default=0.0, description="Average daily carbohydrate intake (g)"
    )
    avg_daily_fiber_g: float = Field(default=0.0, description="Average daily fiber intake (g)")
    daily_logs: list[DailyFoodLog] = Field(
        default_factory=list, description="Logs for each tracked day"
    )
