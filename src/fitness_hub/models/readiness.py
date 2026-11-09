"""Domain models for systemic physical readiness scores and consolidated reports."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fitness_hub.models.biometrics import BiometricSnapshot
from fitness_hub.models.nutrition import DailyNutritionSummary
from fitness_hub.models.workouts import WorkoutSession

ReadinessStatus = Literal["OPTIMAL", "MODERATE", "RECOVERY_NEEDED"]


class ReadinessScore(BaseModel):
    """Detailed breakdown of systemic readiness scoring."""

    model_config = ConfigDict(extra="ignore")

    score: int = Field(ge=0, le=100, description="Overall systemic readiness index (0-100)")
    status: ReadinessStatus = Field(description="Qualitative training readiness category")
    sleep_subscore: float = Field(
        ge=0.0, le=100.0, description="Sleep duration and quality component (40%)"
    )
    biometrics_subscore: float = Field(
        ge=0.0, le=100.0, description="Resting HR and activity component (20%)"
    )
    workout_strain_subscore: float = Field(
        ge=0.0, le=100.0, description="Recent tonnage and fatigue component (25%)"
    )
    nutrition_subscore: float = Field(
        ge=0.0, le=100.0, description="Macronutrient / protein component (15%)"
    )


class DailyReadinessReport(BaseModel):
    """Flagship composite report aggregating biometrics, training, nutrition, and readiness."""

    model_config = ConfigDict(extra="ignore")

    date: str = Field(description="Report evaluation date (YYYY-MM-DD)")
    readiness_score: int = Field(ge=0, le=100, description="Deterministic readiness score (0-100)")
    status: ReadinessStatus = Field(
        description="Systemic status: OPTIMAL, MODERATE, or RECOVERY_NEEDED"
    )
    biometrics: BiometricSnapshot | None = Field(
        default=None, description="Day's biometric snapshot"
    )
    last_workout: WorkoutSession | None = Field(
        default=None, description="Most recent workout session"
    )
    nutrition: DailyNutritionSummary | None = Field(
        default=None, description="Previous day nutrition summary"
    )
    coaching_notes: list[str] = Field(
        default_factory=list, description="Deterministic actionable coaching flags"
    )
