"""Pydantic data models for wearable biometric data (activity, sleep, heart rate)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HeartRateInfo(BaseModel):
    """Heart rate metrics for a given period or day."""

    model_config = ConfigDict(extra="ignore")

    resting_bpm: int | None = Field(
        default=None, description="Resting heart rate in beats per minute"
    )
    avg_bpm: int | None = Field(default=None, description="Average heart rate in bpm")
    min_bpm: int | None = Field(default=None, description="Minimum recorded heart rate in bpm")
    max_bpm: int | None = Field(default=None, description="Maximum recorded heart rate in bpm")


class SleepStages(BaseModel):
    """Time spent in distinct sleep stages in seconds."""

    model_config = ConfigDict(extra="ignore")

    deep_seconds: int = Field(default=0, description="Deep (slow-wave) sleep duration in seconds")
    rem_seconds: int = Field(default=0, description="REM sleep duration in seconds")
    light_seconds: int = Field(default=0, description="Light sleep duration in seconds")
    awake_seconds: int = Field(default=0, description="Awake time during sleep session in seconds")

    @property
    def deep_hours(self) -> float:
        return round(self.deep_seconds / 3600.0, 2)

    @property
    def rem_hours(self) -> float:
        return round(self.rem_seconds / 3600.0, 2)


class SleepSession(BaseModel):
    """Details for a single sleep session."""

    model_config = ConfigDict(extra="ignore")

    session_id: str | None = Field(default=None, description="Unique sleep session identifier")
    date: str = Field(description="Date associated with sleep session (YYYY-MM-DD)")
    start_time: str | None = Field(
        default=None, description="Start timestamp of sleep session (ISO 8601)"
    )
    end_time: str | None = Field(
        default=None, description="End timestamp of sleep session (ISO 8601)"
    )
    total_sleep_seconds: int = Field(
        default=0, description="Total sleep time in seconds excluding awake time"
    )
    time_in_bed_seconds: int | None = Field(
        default=None, description="Total time in bed in seconds"
    )
    efficiency_percent: float | None = Field(
        default=None, description="Sleep efficiency percentage (0-100)"
    )
    stages: SleepStages = Field(
        default_factory=SleepStages, description="Breakdown of sleep stages"
    )
    resting_heart_rate: int | None = Field(
        default=None, description="Resting heart rate during sleep"
    )
    hrv_sdnn: float | None = Field(
        default=None, description="Standard deviation of NN intervals (SDNN) in ms"
    )
    hrv_rmssd: float | None = Field(
        default=None, description="Root mean square of successive differences in ms"
    )
    sleep_score: int | None = Field(
        default=None, description="Provider composite sleep score (0-100)"
    )

    @property
    def duration_hours(self) -> float:
        """Total sleep duration in hours."""
        return round(self.total_sleep_seconds / 3600.0, 2)


class DailyActivity(BaseModel):
    """Daily summary of physical activity and energy expenditure."""

    model_config = ConfigDict(extra="ignore")

    date: str = Field(description="Record date (YYYY-MM-DD)")
    steps: int = Field(default=0, description="Total step count")
    distance_meters: float = Field(default=0.0, description="Total distance moved in meters")
    active_calories_kcal: float = Field(
        default=0.0, description="Active energy burned in kilocalories"
    )
    total_calories_kcal: float = Field(
        default=0.0, description="Total daily energy expenditure (TDEE) in kcal"
    )
    active_minutes: int = Field(
        default=0, description="Minutes of moderate-to-vigorous physical activity"
    )
    heart_rate: HeartRateInfo = Field(
        default_factory=HeartRateInfo, description="Daily heart rate metrics"
    )
    intensity_minutes: dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of intensity minutes (e.g. light, moderate, vigorous)",
    )


class BiometricsSummary(BaseModel):
    """Aggregated biometrics across a specified date range."""

    model_config = ConfigDict(extra="ignore")

    start_date: str = Field(description="Start date of period (YYYY-MM-DD)")
    end_date: str = Field(description="End date of period (YYYY-MM-DD)")
    days_count: int = Field(default=0, description="Number of days in the summary")
    avg_daily_steps: float = Field(default=0.0, description="Average daily step count")
    avg_active_calories: float = Field(
        default=0.0, description="Average daily active calories burned (kcal)"
    )
    avg_sleep_hours: float = Field(
        default=0.0, description="Average nightly sleep duration in hours"
    )
    avg_resting_hr: float | None = Field(
        default=None, description="Average resting heart rate in bpm"
    )
    daily_activities: list[DailyActivity] = Field(default_factory=list)
    sleep_sessions: list[SleepSession] = Field(default_factory=list)
