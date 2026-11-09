"""Pydantic data models for workout tracking, strength exercises, sets, and volume."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SetType(StrEnum):
    """Classification of an exercise set."""

    WARMUP = "warmup"
    NORMAL = "normal"
    FAILURE = "failure"
    DROP_SET = "drop_set"


class WorkoutSet(BaseModel):
    """A single set executed during an exercise."""

    model_config = ConfigDict(extra="ignore")

    index: int = Field(default=0, description="Order of the set within the exercise")
    type: str = Field(
        default="normal",
        description="Type of set: 'normal', 'warmup', 'failure', or 'drop_set'",
    )
    weight_kg: float | None = Field(default=None, description="Weight used in kilograms")
    reps: int | None = Field(default=None, description="Number of repetitions completed")
    rpe: float | None = Field(
        default=None, description="Rate of Perceived Exertion (scale 6.0 - 10.0)"
    )
    distance_meters: float | None = Field(
        default=None, description="Distance for cardio or weighted carry"
    )
    duration_seconds: float | None = Field(
        default=None, description="Set duration or isometric hold in seconds"
    )

    @property
    def is_working_set(self) -> bool:
        """Warmups are excluded from working set count and primary volume."""
        return self.type.lower() != "warmup"

    @property
    def volume_kg(self) -> float:
        """Calculated tonnage for this set: weight_kg * reps."""
        if self.weight_kg is not None and self.reps is not None and self.is_working_set:
            return round(self.weight_kg * self.reps, 2)
        return 0.0

    @property
    def estimated_1rm(self) -> float | None:
        """Estimated 1 Rep Max using the Epley formula: weight * (1 + reps / 30)."""
        if self.weight_kg is not None and self.reps is not None and self.reps > 0:
            if self.reps == 1:
                return round(self.weight_kg, 2)
            return round(self.weight_kg * (1.0 + self.reps / 30.0), 2)
        return None


class Exercise(BaseModel):
    """An exercise performed in a workout consisting of multiple sets."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = Field(default=None, description="Unique exercise log ID")
    title: str = Field(description="Name of the exercise (e.g. 'Barbell Bench Press')")
    exercise_template_id: str | None = Field(
        default=None,
        description="Template ID in Hevy library",
    )
    notes: str | None = Field(default=None, description="Athlete or coach notes for this exercise")
    sets: list[WorkoutSet] = Field(default_factory=list, description="Sets performed")

    @property
    def total_volume_kg(self) -> float:
        """Sum of volume (tonnage) across all working sets."""
        return round(sum(s.volume_kg for s in self.sets), 2)

    @property
    def working_sets_count(self) -> int:
        """Count of working sets (excluding warmups)."""
        return sum(1 for s in self.sets if s.is_working_set)

    @property
    def max_weight_kg(self) -> float | None:
        """Highest weight lifted during this exercise."""
        weights = [s.weight_kg for s in self.sets if s.weight_kg is not None]
        return max(weights) if weights else None

    @property
    def best_estimated_1rm(self) -> float | None:
        """Best estimated 1RM across all sets in this exercise."""
        estimates = [s.estimated_1rm for s in self.sets if s.estimated_1rm is not None]
        return max(estimates) if estimates else None

    @property
    def avg_rpe(self) -> float | None:
        """Average RPE across logged working sets."""
        rpes = [s.rpe for s in self.sets if s.rpe is not None and s.is_working_set]
        return round(sum(rpes) / len(rpes), 2) if rpes else None


class Workout(BaseModel):
    """Complete workout record with exercises and aggregate workload metrics."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="Unique workout identifier")
    title: str = Field(description="Workout title (e.g. 'Upper Body Push')")
    description: str = Field(default="", description="Workout notes or description")
    start_time: str = Field(description="Start timestamp in ISO 8601 format")
    end_time: str | None = Field(default=None, description="End timestamp in ISO 8601 format")
    exercises: list[Exercise] = Field(default_factory=list, description="List of logged exercises")

    @property
    def total_tonnage_kg(self) -> float:
        """Total volume in kilograms across all exercises and working sets."""
        return round(sum(ex.total_volume_kg for ex in self.exercises), 2)

    @property
    def total_working_sets(self) -> int:
        """Total count of working sets across all exercises."""
        return sum(ex.working_sets_count for ex in self.exercises)

    @property
    def avg_rpe(self) -> float | None:
        """Average RPE for the entire workout."""
        rpes = [ex.avg_rpe for ex in self.exercises if ex.avg_rpe is not None]
        return round(sum(rpes) / len(rpes), 2) if rpes else None

    @property
    def duration_minutes(self) -> float | None:
        """Workout duration in minutes calculated from start and end times."""
        if not self.end_time:
            return None
        try:
            start_dt = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
            duration_secs = (end_dt - start_dt).total_seconds()
            return round(duration_secs / 60.0, 1)
        except Exception:
            return None


class WorkoutSummary(BaseModel):
    """Aggregated training metrics over a specified period."""

    model_config = ConfigDict(extra="ignore")

    period_start: str | None = Field(default=None, description="Start date of period")
    period_end: str | None = Field(default=None, description="End date of period")
    total_workouts: int = Field(default=0, description="Total number of workouts logged")
    total_tonnage_kg: float = Field(default=0.0, description="Total volume lifted in kilograms")
    total_working_sets: int = Field(default=0, description="Total working sets completed")
    avg_workout_rpe: float | None = Field(default=None, description="Average RPE across workouts")
    workouts: list[Workout] = Field(default_factory=list, description="Individual workouts")
