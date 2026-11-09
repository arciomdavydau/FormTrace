"""Stable MCP response contracts for analytics and Hevy operation envelopes."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from fitness_hub.models.workouts import WorkoutSession

Count = Annotated[int, Field(ge=0)]


class ResponseModel(BaseModel):
    """Reject unintended fields in contracts owned by the hub."""

    model_config = ConfigDict(extra="forbid", strict=True)


class SnapshotSource(ResponseModel):
    provider: str
    fetched_at: str
    complete: bool
    cache_ttl_seconds: Count


class DirectSource(ResponseModel):
    provider: str
    fetched_at: str


class DatePeriod(ResponseModel):
    start: str
    end: str


class LocalDatePeriod(DatePeriod):
    timezone: str


class WorkoutSummary(ResponseModel):
    id: str
    title: str
    start_time: str
    working_sets: Count


class MuscleGroupSummary(ResponseModel):
    basis: str
    classified_working_sets: Count
    unclassified_working_sets: Count
    primary_working_sets: dict[str, Count]
    secondary_involvement_sets: dict[str, Count]


class TrainingSummary(ResponseModel):
    workouts_count: Count
    working_sets: Count
    warmup_sets: Count
    unknown_type_sets: Count
    workouts: list[WorkoutSummary]
    muscle_groups: MuscleGroupSummary

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        groups = self.muscle_groups
        if self.workouts_count != len(self.workouts):
            raise ValueError("workouts_count must match the returned workouts")
        if self.working_sets != sum(workout.working_sets for workout in self.workouts):
            raise ValueError("working_sets must equal the sum of workout working sets")
        if self.working_sets != groups.classified_working_sets + groups.unclassified_working_sets:
            raise ValueError("classified and unclassified sets must add up to working sets")
        if sum(groups.primary_working_sets.values()) != groups.classified_working_sets:
            raise ValueError("primary muscle-group counts must add up to classified sets")
        return self


class TrainingReport(ResponseModel):
    period: LocalDatePeriod
    previous_period: DatePeriod
    source: SnapshotSource
    current: TrainingSummary
    previous: TrainingSummary
    warnings: list[str]


class ExerciseMatch(ResponseModel):
    id: str | int | None
    title: str | None
    primary_muscle_group: str | None


class ExerciseSearchResult(ResponseModel):
    source: SnapshotSource
    total_matches: Count
    truncated: bool
    exercises: list[ExerciseMatch]


class ProgressionSet(ResponseModel):
    type: Literal["normal", "failure", "dropset"]
    weight_kg: float | None
    reps: int | None
    rpe: float | None
    duration_seconds: float | None
    distance_meters: float | None
    custom_metric: float | None


class ProgressionSession(ResponseModel):
    workout_id: str
    start_time: str
    exercise: str
    working_sets: list[ProgressionSet]
    unknown_type_sets: Count


class ExerciseProgressionReport(ResponseModel):
    exercise_id: str
    period: LocalDatePeriod
    source: SnapshotSource
    sessions: list[ProgressionSession]
    note: str


class WorkoutDetails(ResponseModel):
    source: SnapshotSource
    workout: WorkoutSession


class HevyReadResult(ResponseModel):
    source: DirectSource
    # Hevy owns this payload and may add or change fields independently of the hub.
    data: dict[str, Any]


class HevyWritePreview(ResponseModel):
    dry_run: Literal[True]
    provider: str
    operation: str
    resource: str
    payload: dict[str, Any]
    message: str


class HevyWriteResult(ResponseModel):
    dry_run: Literal[False]
    source: DirectSource
    data: dict[str, Any]


# A top-level union is represented explicitly so existing MCP result objects are
# not wrapped in an additional {"result": ...} field by the framework.
HEVY_WRITE_OUTPUT_SCHEMA = TypeAdapter(HevyWritePreview | HevyWriteResult).json_schema()
HEVY_WRITE_OUTPUT_SCHEMA["type"] = "object"
