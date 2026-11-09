"""Domain models for strength workouts, exercises, working sets, and deterministic tonnage math."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SetType(StrEnum):
    """Classification of an individual set in Hevy."""

    WARMUP = "warmup"
    NORMAL = "normal"
    FAILURE = "failure"
    DROPSET = "dropset"


class ExerciseSet(BaseModel):
    """An individual set executed within an exercise."""

    model_config = ConfigDict(extra="ignore")

    index: int = Field(default=0, description="0-indexed sequence of the set")
    set_type: SetType = Field(default=SetType.NORMAL, description="Set type classification")
    weight_kg: float | None = Field(default=None, description="Weight lifted in kilograms")
    reps: int | None = Field(default=None, description="Repetitions completed")
    rpe: float | None = Field(default=None, description="Rate of perceived exertion (6.0-10.0)")
    distance_meters: float | None = Field(
        default=None, description="Distance for loaded carries/cardio"
    )
    duration_seconds: float | None = Field(default=None, description="Duration in seconds")

    @property
    def is_working_set(self) -> bool:
        """Return True if set is NOT a warm-up."""
        return self.set_type != SetType.WARMUP

    @property
    def volume_kg(self) -> float:
        """Volume (weight * reps) strictly for working sets with non-null weight and reps."""
        if self.is_working_set and self.weight_kg is not None and self.reps is not None:
            return round(self.weight_kg * self.reps, 2)
        return 0.0


class ExerciseLog(BaseModel):
    """An exercise performed in a workout session containing multiple sets."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = Field(default=None, description="Unique exercise instance ID")
    title: str = Field(description="Exercise name (e.g., 'Barbell Deadlift')")
    exercise_template_id: str | None = Field(
        default=None, description="Hevy exercise template UUID"
    )
    notes: str | None = Field(default=None, description="Set execution or coaching notes")
    sets: list[ExerciseSet] = Field(default_factory=list, description="Sets performed")

    @property
    def working_tonnage_kg(self) -> float:
        """Sum of (weight_kg * reps) strictly for working sets (excluding warmup sets)."""
        return round(sum(s.volume_kg for s in self.sets), 2)

    @property
    def total_working_sets(self) -> int:
        """Total count of non-warmup sets."""
        return sum(1 for s in self.sets if s.is_working_set)

    @property
    def avg_rpe(self) -> float | None:
        """Average RPE strictly across working sets with recorded RPE."""
        rpes = [s.rpe for s in self.sets if s.is_working_set and s.rpe is not None]
        return round(sum(rpes) / len(rpes), 2) if rpes else None


class WorkoutSession(BaseModel):
    """A complete workout session recorded in Hevy."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="Unique workout identifier")
    title: str = Field(description="Workout title (e.g., 'Upper Body Push')")
    description: str = Field(default="", description="Workout notes or remarks")
    start_time: str = Field(description="ISO 8601 start timestamp")
    end_time: str | None = Field(default=None, description="ISO 8601 end timestamp")
    exercises: list[ExerciseLog] = Field(default_factory=list, description="Exercises performed")

    @property
    def working_tonnage_kg(self) -> float:
        """Total working tonnage across all exercises in the session."""
        return round(sum(ex.working_tonnage_kg for ex in self.exercises), 2)

    @property
    def total_working_sets(self) -> int:
        """Total count of non-warmup sets across all exercises."""
        return sum(ex.total_working_sets for ex in self.exercises)

    @property
    def avg_rpe(self) -> float | None:
        """Average RPE across all working sets in the session."""
        all_working_rpes = [
            s.rpe
            for ex in self.exercises
            for s in ex.sets
            if s.is_working_set and s.rpe is not None
        ]
        if not all_working_rpes:
            return None
        return round(sum(all_working_rpes) / len(all_working_rpes), 2)

    @property
    def duration_minutes(self) -> float | None:
        """Workout duration in minutes derived from start and end times."""
        if not self.end_time:
            return None
        try:
            start_dt = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
            return round((end_dt - start_dt).total_seconds() / 60.0, 1)
        except Exception:
            return None
