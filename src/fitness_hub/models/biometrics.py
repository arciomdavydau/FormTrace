"""Domain models for wearable telemetry (Open Wearables schema: activity, sleep, resting HR)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SleepMetrics(BaseModel):
    """Nightly sleep analysis metrics from wearable devices."""

    model_config = ConfigDict(extra="ignore")

    date: str = Field(description="Date associated with sleep session (YYYY-MM-DD)")
    total_sleep_minutes: int = Field(
        ge=0, description="Total minutes of sleep (excluding wake time)"
    )
    deep_sleep_minutes: int = Field(
        default=0, ge=0, description="Deep (slow-wave) sleep in minutes"
    )
    rem_sleep_minutes: int = Field(default=0, ge=0, description="REM sleep in minutes")
    sleep_efficiency_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Sleep efficiency as percentage (0.0 to 100.0)",
    )
    resting_hr_bpm: int | None = Field(
        default=None, description="Average resting heart rate during sleep"
    )
    hrv_sdnn_ms: float | None = Field(
        default=None, description="Heart rate variability (SDNN) in milliseconds"
    )

    @property
    def duration_hours(self) -> float:
        """Total sleep duration converted to hours."""
        return round(self.total_sleep_minutes / 60.0, 2)


class DailyActivity(BaseModel):
    """Daily movement and activity telemetry from wearable devices."""

    model_config = ConfigDict(extra="ignore")

    date: str = Field(description="Record date (YYYY-MM-DD)")
    steps: int = Field(default=0, ge=0, description="Total steps taken")
    active_calories: int = Field(default=0, ge=0, description="Active energy burned in kcal")
    resting_hr_bpm: int = Field(default=60, ge=30, le=220, description="Resting heart rate in bpm")
    distance_meters: float = Field(default=0.0, ge=0.0, description="Distance traversed in meters")


class BiometricSnapshot(BaseModel):
    """Consolidated biometric view for a specific day."""

    model_config = ConfigDict(extra="ignore")

    date: str = Field(description="Snapshot date (YYYY-MM-DD)")
    activity: DailyActivity | None = Field(default=None, description="Physical activity metrics")
    sleep: SleepMetrics | None = Field(default=None, description="Sleep session metrics")
