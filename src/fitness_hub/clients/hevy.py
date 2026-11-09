"""Client for Hevy API v1 fetching strength training sessions, exercises, sets, and volume."""

from __future__ import annotations

import logging
from typing import Any

from fitness_hub.clients.base import BaseAsyncClient
from fitness_hub.config import Settings, get_settings
from fitness_hub.models.workouts import (
    ExerciseLog,
    ExerciseSet,
    SetType,
    WorkoutSession,
)

logger = logging.getLogger(__name__)


class HevyClient(BaseAsyncClient):
    """Asynchronous client communicating with Hevy Public REST API (v1)."""

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        super().__init__(
            base_url=cfg.hevy_api_base_url,
            timeout=cfg.request_timeout,
            max_retries=cfg.max_retries,
        )
        self.api_key = cfg.hevy_api_key

    def _endpoint(self, path: str) -> str:
        """Ensure path correctly handles whether base_url includes /v1 or not."""
        clean = path.lstrip("/")
        if self.base_url.endswith("/v1"):
            if clean.startswith("v1/"):
                clean = clean[3:]
        elif not clean.startswith("v1/"):
            clean = f"v1/{clean}"
        return f"/{clean}"

    @property
    def headers(self) -> dict[str, str]:
        """Headers required by Hevy API."""
        hdrs: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            hdrs["api-key"] = self.api_key
            hdrs["x-api-key"] = self.api_key
        return hdrs

    def _parse_set_type(self, raw_type: str | None) -> SetType:
        """Map raw string from Hevy to SetType enum safely."""
        if not raw_type:
            return SetType.NORMAL
        val = raw_type.lower().replace("_", "").replace("-", "")
        if "warmup" in val:
            return SetType.WARMUP
        if "failure" in val:
            return SetType.FAILURE
        if "drop" in val:
            return SetType.DROPSET
        return SetType.NORMAL

    def _parse_workout(self, item: dict[str, Any]) -> WorkoutSession:
        """Parse nested Hevy workout JSON into structured WorkoutSession."""
        exercises: list[ExerciseLog] = []
        for ex_data in item.get("exercises", []):
            sets: list[ExerciseSet] = []
            for idx, s in enumerate(ex_data.get("sets", [])):
                set_type = self._parse_set_type(s.get("type") or s.get("set_type"))
                sets.append(
                    ExerciseSet(
                        index=int(s.get("index", idx)),
                        set_type=set_type,
                        weight_kg=float(s["weight_kg"]) if s.get("weight_kg") is not None else None,
                        reps=int(s["reps"]) if s.get("reps") is not None else None,
                        rpe=float(s["rpe"]) if s.get("rpe") is not None else None,
                        distance_meters=float(s["distance_meters"])
                        if s.get("distance_meters") is not None
                        else None,
                        duration_seconds=float(s["duration_seconds"])
                        if s.get("duration_seconds") is not None
                        else None,
                    )
                )

            exercises.append(
                ExerciseLog(
                    id=ex_data.get("id"),
                    title=ex_data.get("title") or ex_data.get("name") or "Exercise",
                    exercise_template_id=ex_data.get("exercise_template_id"),
                    notes=ex_data.get("notes"),
                    sets=sets,
                )
            )

        return WorkoutSession(
            id=str(item.get("id", "")),
            title=item.get("title") or "Workout",
            description=item.get("description") or "",
            start_time=item.get("start_time", ""),
            end_time=item.get("end_time"),
            exercises=exercises,
        )

    async def get_recent_workouts(self, limit: int = 5) -> list[WorkoutSession]:
        """
        Fetch recent workouts from Hevy.
        Hits GET /workouts?page=1&pageSize={limit}.
        """
        params = {"page": 1, "pageSize": limit}
        path = self._endpoint("workouts")
        data = await self.request("GET", path, headers=self.headers, params=params)

        raw_list: list[dict[str, Any]] = []
        if isinstance(data, dict):
            raw_list = data.get("workouts", [])
        elif isinstance(data, list):
            raw_list = data

        return [self._parse_workout(w) for w in raw_list]

    async def get_workout(self, workout_id: str) -> WorkoutSession:
        """Fetch details of a specific workout by ID."""
        path = self._endpoint(f"workouts/{workout_id}")
        data = await self.request("GET", path, headers=self.headers)
        raw = data.get("workout", data) if isinstance(data, dict) else {}
        return self._parse_workout(raw)
