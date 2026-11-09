"""Domain models for strength workouts, exercises, and recorded sets."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SetType(StrEnum):
    """Classification of an individual set in Hevy."""

    WARMUP = "warmup"
    NORMAL = "normal"
    FAILURE = "failure"
    DROPSET = "dropset"
    UNKNOWN = "unknown"


class ExerciseSet(BaseModel):
    """An individual set executed within an exercise."""

    model_config = ConfigDict(extra="ignore")

    index: int = Field(default=0, description="0-indexed sequence of the set")
    set_type: SetType = Field(default=SetType.UNKNOWN, description="Set type classification")
    weight_kg: float | None = Field(default=None, description="Weight lifted in kilograms")
    reps: int | None = Field(default=None, description="Repetitions completed")
    rpe: float | None = Field(default=None, description="Rate of perceived exertion (6.0-10.0)")
    distance_meters: float | None = Field(
        default=None, description="Distance for loaded carries/cardio"
    )
    duration_seconds: float | None = Field(default=None, description="Duration in seconds")

    @property
    def is_working_set(self) -> bool:
        """Only known non-warmup types count as working sets."""
        return self.set_type in {SetType.NORMAL, SetType.FAILURE, SetType.DROPSET}


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


class WorkoutSession(BaseModel):
    """A complete workout session recorded in Hevy."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="Unique workout identifier")
    title: str = Field(description="Workout title (e.g., 'Upper Body Push')")
    description: str = Field(default="", description="Workout notes or remarks")
    start_time: str = Field(description="ISO 8601 start timestamp")
    end_time: str | None = Field(default=None, description="ISO 8601 end timestamp")
    exercises: list[ExerciseLog] = Field(default_factory=list, description="Exercises performed")
