"""Hevy REST API client for strength workouts, sets, exercises, and volume tracking."""

from __future__ import annotations

import logging
from typing import Any, cast

from src.clients.base import (
    BaseAsyncHTTPClient,
    ConfigurationError,
)
from src.config import Settings, get_settings
from src.models.workout import (
    Exercise,
    Workout,
    WorkoutSet,
    WorkoutSummary,
)

logger = logging.getLogger(__name__)


class HevyClient(BaseAsyncHTTPClient):
    """Client for interacting with the Hevy Public API (v1)."""

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        super().__init__(
            base_url=cfg.hevy_api_url,
            timeout=cfg.hevy_timeout,
            max_retries=cfg.max_retries,
            backoff_factor=cfg.backoff_factor,
        )
        self.api_key = cfg.hevy_api_key.get_secret_value()

    def _endpoint(self, path: str) -> str:
        """Normalize endpoint path taking into account if base_url ends in /v1."""
        clean_path = path.lstrip("/")
        if self.base_url.endswith("/v1"):
            if clean_path.startswith("v1/"):
                clean_path = clean_path[3:]
        elif not clean_path.startswith("v1/"):
            clean_path = f"v1/{clean_path}"
        return f"/{clean_path}"

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

    def _ensure_configured(self) -> None:
        """Verify that Hevy API key is present."""
        if not self.api_key:
            raise ConfigurationError(
                "HEVY_API_KEY is not configured. "
                "Please obtain an API key from hevy.com/settings?developer and configure it."
            )

    def _parse_workout(self, item: dict[str, Any]) -> Workout:
        """Transform raw Hevy workout JSON into structured Workout model."""
        exercises: list[Exercise] = []
        for ex_data in item.get("exercises", []):
            sets: list[WorkoutSet] = []
            for idx, set_data in enumerate(ex_data.get("sets", [])):
                sets.append(
                    WorkoutSet(
                        index=idx,
                        type=set_data.get("type", "normal") or "normal",
                        weight_kg=set_data.get("weight_kg"),
                        reps=set_data.get("reps"),
                        rpe=set_data.get("rpe"),
                        distance_meters=set_data.get("distance_meters"),
                        duration_seconds=set_data.get("duration_seconds"),
                    )
                )

            exercises.append(
                Exercise(
                    id=ex_data.get("id"),
                    title=ex_data.get("title") or ex_data.get("name") or "Exercise",
                    exercise_template_id=ex_data.get("exercise_template_id"),
                    notes=ex_data.get("notes"),
                    sets=sets,
                )
            )

        return Workout(
            id=str(item.get("id", "")),
            title=item.get("title") or "Workout",
            description=item.get("description") or "",
            start_time=item.get("start_time", ""),
            end_time=item.get("end_time"),
            exercises=exercises,
        )

    async def get_workout_count(self) -> int:
        """Fetch total count of workouts on the account."""
        self._ensure_configured()
        data = await self.request("GET", self._endpoint("workouts/count"), headers=self.headers)
        if isinstance(data, dict):
            return int(data.get("workout_count", 0))
        return 0

    async def get_workouts(
        self,
        page: int = 1,
        page_size: int = 10,
        since: str | None = None,
    ) -> list[Workout]:
        """
        Fetch paginated list of workouts from Hevy.

        Args:
            page: Page number (1-indexed)
            page_size: Number of workouts per page (max 10)
            since: ISO 8601 date string to filter workouts created/updated after
        """
        self._ensure_configured()
        params: dict[str, Any] = {
            "page": page,
            "pageSize": page_size,
        }
        if since:
            params["since"] = since

        data = await self.request(
            "GET", self._endpoint("workouts"), headers=self.headers, params=params
        )
        raw_list: list[dict[str, Any]] = []
        if isinstance(data, dict):
            raw_list = data.get("workouts", [])
        elif isinstance(data, list):
            raw_list = data

        return [self._parse_workout(item) for item in raw_list]

    async def get_workout(self, workout_id: str) -> Workout:
        """Fetch full details for a single workout by UUID."""
        self._ensure_configured()
        data = await self.request(
            "GET", self._endpoint(f"workouts/{workout_id}"), headers=self.headers
        )
        raw = data.get("workout", data) if isinstance(data, dict) else {}
        return self._parse_workout(raw)

    async def get_exercise_templates(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch available exercise templates from Hevy catalog."""
        self._ensure_configured()
        params = {"page": page, "pageSize": page_size}
        data = await self.request(
            "GET", self._endpoint("exercise_templates"), headers=self.headers, params=params
        )
        if isinstance(data, dict):
            templates = data.get("exercise_templates", [])
            return cast(list[dict[str, Any]], templates)
        if isinstance(data, list):
            return cast(list[dict[str, Any]], data)
        return []

    async def create_workout(self, workout_payload: dict[str, Any]) -> Workout:
        """
        Log or create a new workout session in Hevy.

        Payload should be in format:
        {
            "workout": {
                "title": "Leg Day",
                "start_time": "2026-11-09T18:00:00Z",
                "exercises": [...]
            }
        }
        """
        self._ensure_configured()
        body = workout_payload if "workout" in workout_payload else {"workout": workout_payload}
        data = await self.request(
            "POST", self._endpoint("workouts"), headers=self.headers, json=body
        )
        raw = data.get("workout", data) if isinstance(data, dict) else {}
        return self._parse_workout(raw)

    async def get_workout_summary(
        self,
        page_size: int = 20,
        since: str | None = None,
    ) -> WorkoutSummary:
        """Fetch workouts and calculate aggregate volume and workload metrics."""
        workouts = await self.get_workouts(page=1, page_size=page_size, since=since)
        total_tonnage = round(sum(w.total_tonnage_kg for w in workouts), 2)
        total_sets = sum(w.total_working_sets for w in workouts)

        rpes = [w.avg_rpe for w in workouts if w.avg_rpe is not None]
        avg_rpe = round(sum(rpes) / len(rpes), 2) if rpes else None

        period_start = workouts[-1].start_time[:10] if workouts else None
        period_end = workouts[0].start_time[:10] if workouts else None

        return WorkoutSummary(
            period_start=period_start,
            period_end=period_end,
            total_workouts=len(workouts),
            total_tonnage_kg=total_tonnage,
            total_working_sets=total_sets,
            avg_workout_rpe=avg_rpe,
            workouts=workouts,
        )
