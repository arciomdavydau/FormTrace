"""Validated payloads for Hevy's documented workout and routine write APIs."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

SetKind = Literal["normal", "warmup", "failure", "dropset"]
MuscleGroup = Literal[
    "abdominals",
    "shoulders",
    "biceps",
    "triceps",
    "forearms",
    "quadriceps",
    "hamstrings",
    "calves",
    "glutes",
    "abductors",
    "adductors",
    "lats",
    "upper_back",
    "traps",
    "lower_back",
    "chest",
    "cardio",
    "neck",
    "full_body",
    "other",
]
Equipment = Literal[
    "none",
    "barbell",
    "dumbbell",
    "kettlebell",
    "machine",
    "plate",
    "resistance_band",
    "suspension",
    "other",
]
ExerciseType = Literal[
    "weight_reps",
    "reps_only",
    "bodyweight_reps",
    "bodyweight_assisted_reps",
    "duration",
    "weight_duration",
    "distance_duration",
    "short_distance_weight",
]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkoutSetInput(InputModel):
    type: SetKind = "normal"
    weight_kg: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=0)
    distance_meters: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    custom_metric: float | None = Field(default=None, ge=0)
    rpe: float | None = Field(default=None, ge=6, le=10)

    @field_validator("rpe")
    @classmethod
    def validate_rpe(cls, value: float | None) -> float | None:
        if value is not None and value not in {6, 7, 7.5, 8, 8.5, 9, 9.5, 10}:
            raise ValueError("RPE must be one of Hevy's supported values")
        return value


class WorkoutExerciseInput(InputModel):
    exercise_template_id: str = Field(min_length=1, max_length=128)
    superset_id: int | None = None
    notes: str | None = None
    sets: list[WorkoutSetInput]


class WorkoutCreateInput(InputModel):
    title: str = Field(min_length=1)
    description: str | None = None
    start_time: AwareDatetime
    end_time: AwareDatetime
    is_private: bool = True
    exercises: list[WorkoutExerciseInput]

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if self.end_time < self.start_time:
            raise ValueError("end_time must not be earlier than start_time")
        return self


class WorkoutUpdateInput(WorkoutCreateInput):
    # Hevy documents PUT using the full workout payload. Require privacy explicitly
    # so omission cannot silently change an existing workout's visibility.
    is_private: bool


class RepRangeInput(InputModel):
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("rep_range.end must be at least rep_range.start")
        return self


class RoutineSetInput(InputModel):
    type: SetKind = "normal"
    weight_kg: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=0)
    distance_meters: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    custom_metric: float | None = Field(default=None, ge=0)
    rep_range: RepRangeInput | None = None


class RoutineExerciseInput(InputModel):
    exercise_template_id: str = Field(min_length=1, max_length=128)
    superset_id: int | None = None
    rest_seconds: int | None = Field(default=None, ge=0)
    notes: str | None = None
    sets: list[RoutineSetInput]


class RoutineCreateInput(InputModel):
    title: str = Field(min_length=1)
    folder_id: int | None = None
    notes: str | None = None
    exercises: list[RoutineExerciseInput]


class RoutineUpdateInput(RoutineCreateInput):
    folder_id: int | None
    notes: str | None


class ExerciseCreateInput(InputModel):
    title: str = Field(min_length=1)
    exercise_type: ExerciseType
    equipment_category: Equipment
    muscle_group: MuscleGroup
    other_muscles: list[MuscleGroup] = Field(default_factory=list)


class RoutineFolderCreateInput(InputModel):
    title: str = Field(min_length=1)
