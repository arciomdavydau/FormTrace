"""Read-only training summaries with explicit dates, source and coverage."""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fitness_hub.models.workouts import SetType, WorkoutSession

MUSCLES = {
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
    "neck",
}


class WorkoutSource(Protocol):
    async def get_all_workouts(self) -> list[WorkoutSession]: ...
    async def get_exercise_templates(self) -> list[dict[str, Any]]: ...
    async def api_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
    async def close(self) -> None: ...


@dataclass
class Snapshot:
    workouts: list[WorkoutSession]
    templates: list[dict[str, Any]]
    fetched_at: datetime


def _dates(start_date: str, end_date: str, timezone_name: str) -> tuple[date, date, ZoneInfo]:
    try:
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
        zone = ZoneInfo(timezone_name)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("Use YYYY-MM-DD dates and a valid IANA timezone") from exc
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    if (end - start).days > 365:
        raise ValueError("The maximum report period is 366 days")
    return start, end, zone


def _local_date(workout: WorkoutSession, zone: ZoneInfo) -> date:
    try:
        value = datetime.fromisoformat(workout.start_time.replace("Z", "+00:00"))
        if value.utcoffset() is None:
            raise ValueError("Missing timezone")
        return value.astimezone(zone).date()
    except (ValueError, OverflowError) as exc:
        raise ValueError("A Hevy workout has an invalid or timezone-free start time") from exc


def _period_workouts(
    workouts: list[WorkoutSession], start: date, end: date, zone: ZoneInfo
) -> list[WorkoutSession]:
    return sorted(
        (w for w in workouts if start <= _local_date(w, zone) <= end),
        key=lambda w: datetime.fromisoformat(w.start_time.replace("Z", "+00:00")),
    )


def _summary(workouts: list[WorkoutSession], templates: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {str(template.get("id")): template for template in templates if template.get("id")}
    primary: Counter[str] = Counter()
    secondary: Counter[str] = Counter()
    working = warmups = unknown = unclassified = 0
    sessions: list[dict[str, Any]] = []
    for workout in workouts:
        session_working = 0
        for exercise in workout.exercises:
            sets = [s for s in exercise.sets if s.is_working_set]
            count = len(sets)
            working += count
            session_working += count
            warmups += sum(s.set_type == SetType.WARMUP for s in exercise.sets)
            unknown += sum(s.set_type == SetType.UNKNOWN for s in exercise.sets)
            template = by_id.get(exercise.exercise_template_id or "", {})
            group = template.get("primary_muscle_group")
            if isinstance(group, str) and group in MUSCLES:
                primary[group] += count
            else:
                unclassified += count
            secondary_groups = template.get("secondary_muscle_groups")
            if isinstance(secondary_groups, list):
                for item in {item for item in secondary_groups if isinstance(item, str)}:
                    if item in MUSCLES and item != group:
                        secondary[item] += count
        sessions.append(
            {
                "id": workout.id,
                "title": workout.title,
                "start_time": workout.start_time,
                "working_sets": session_working,
            }
        )
    return {
        "workouts_count": len(workouts),
        "working_sets": working,
        "warmup_sets": warmups,
        "unknown_type_sets": unknown,
        "workouts": sessions,
        "muscle_groups": {
            "basis": "Hevy exercise template primary and secondary groups; recorded working sets",
            "classified_working_sets": working - unclassified,
            "unclassified_working_sets": unclassified,
            "primary_working_sets": dict(sorted(primary.items())),
            "secondary_involvement_sets": dict(sorted(secondary.items())),
        },
    }


class TrainingService:
    """Fetch a consistent-enough snapshot and calculate reports without an LLM."""

    def __init__(self, source: WorkoutSource, provider: str = "hevy", cache_seconds: int = 300):
        self.source = source
        self.provider = provider
        self.cache_seconds = cache_seconds
        self._snapshot: Snapshot | None = None
        self._cached_at = 0.0
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self.source.close()

    async def invalidate(self) -> None:
        """Ensure a later report does not reuse a snapshot after a write attempt."""
        async with self._lock:
            self._snapshot = None
            self._cached_at = 0.0

    async def snapshot(self, refresh: bool = False) -> Snapshot:
        async with self._lock:
            if (
                not refresh
                and self._snapshot is not None
                and time.monotonic() - self._cached_at < self.cache_seconds
            ):
                return self._snapshot
            workouts = await self.source.get_all_workouts()
            templates = await self.source.get_exercise_templates()
            snapshot = Snapshot(workouts, templates, datetime.now(UTC))
            self._snapshot = snapshot
            self._cached_at = time.monotonic()
            return snapshot

    def _source_info(self, snapshot: Snapshot) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "fetched_at": snapshot.fetched_at.isoformat(),
            "complete": True,
            "cache_ttl_seconds": self.cache_seconds,
        }

    async def report(
        self, start_date: str, end_date: str, timezone_name: str, refresh: bool = False
    ) -> dict[str, Any]:
        start, end, zone = _dates(start_date, end_date, timezone_name)
        length = (end - start).days + 1
        previous_end = start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=length - 1)
        snapshot = await self.snapshot(refresh)
        current = _summary(
            _period_workouts(snapshot.workouts, start, end, zone), snapshot.templates
        )
        previous = _summary(
            _period_workouts(snapshot.workouts, previous_start, previous_end, zone),
            snapshot.templates,
        )
        return {
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "timezone": timezone_name,
            },
            "previous_period": {
                "start": previous_start.isoformat(),
                "end": previous_end.isoformat(),
            },
            "source": self._source_info(snapshot),
            "current": current,
            "previous": previous,
            "warnings": [
                "Muscle groups reflect recorded exercise templates, not measured muscle effort.",
                "Secondary involvement overlaps primary sets; do not sum them as distinct sets.",
                "Unknown set types and unclassified working sets are shown separately.",
            ],
        }

    async def search(self, query: str) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")
        snapshot = await self.snapshot()
        matches = [
            t for t in snapshot.templates if query.casefold() in str(t.get("title", "")).casefold()
        ]
        return {
            "source": self._source_info(snapshot),
            "total_matches": len(matches),
            "truncated": len(matches) > 20,
            "exercises": [
                {
                    "id": t.get("id"),
                    "title": t.get("title"),
                    "primary_muscle_group": t.get("primary_muscle_group"),
                }
                for t in matches[:20]
            ],
        }

    async def progression(
        self, exercise_id: str, start_date: str, end_date: str, timezone_name: str
    ) -> dict[str, Any]:
        if not exercise_id.strip():
            raise ValueError("exercise_id must not be empty")
        start, end, zone = _dates(start_date, end_date, timezone_name)
        snapshot = await self.snapshot()
        sessions: list[dict[str, Any]] = []
        for workout in _period_workouts(snapshot.workouts, start, end, zone):
            for exercise in workout.exercises:
                if exercise.exercise_template_id == exercise_id:
                    sessions.append(
                        {
                            "workout_id": workout.id,
                            "start_time": workout.start_time,
                            "exercise": exercise.title,
                            "working_sets": [
                                {
                                    "type": s.set_type.value,
                                    "weight_kg": s.weight_kg,
                                    "reps": s.reps,
                                    "rpe": s.rpe,
                                    "duration_seconds": s.duration_seconds,
                                    "distance_meters": s.distance_meters,
                                    "custom_metric": s.custom_metric,
                                }
                                for s in exercise.sets
                                if s.is_working_set
                            ],
                            "unknown_type_sets": sum(
                                s.set_type == SetType.UNKNOWN for s in exercise.sets
                            ),
                        }
                    )
        return {
            "exercise_id": exercise_id,
            "period": {"start": start_date, "end": end_date, "timezone": timezone_name},
            "source": self._source_info(snapshot),
            "sessions": sessions,
            "note": "Compare weight and repetitions together; no strength change is inferred.",
        }

    async def workout_details(self, workout_id: str) -> dict[str, Any]:
        snapshot = await self.snapshot()
        for workout in snapshot.workouts:
            if workout.id == workout_id:
                return {
                    "source": self._source_info(snapshot),
                    "workout": workout.model_dump(mode="json"),
                }
        raise ValueError("Workout not found in the current source")
