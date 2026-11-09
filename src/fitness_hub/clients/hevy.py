"""Client for Hevy API v1 fetching strength training sessions, exercises, sets, and volume."""

from __future__ import annotations

import logging
from typing import Any

from fitness_hub.clients.base import BaseAsyncClient, UpstreamAPIError
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
        return hdrs

    def _parse_set_type(self, raw_type: str | None) -> SetType:
        """Map raw string from Hevy to SetType enum safely."""
        if raw_type is None:
            return SetType.UNKNOWN
        try:
            return SetType(raw_type.lower())
        except ValueError:
            return SetType.UNKNOWN

    async def api_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call a specific Hevy operation and require an object response."""
        result = await self.request(
            method,
            self._endpoint(path),
            headers=self.headers,
            params=params,
            json=body,
            accept_plain_identifier=(
                method.upper() == "POST" and path.strip("/") == "exercise_templates"
            ),
        )
        if not isinstance(result, dict):
            raise UpstreamAPIError("Unexpected Hevy API response format")
        return result

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
                        custom_metric=float(s["custom_metric"])
                        if s.get("custom_metric") is not None
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

    async def _get_all_pages(
        self, endpoint: str, items_key: str, page_size: int
    ) -> list[dict[str, Any]]:
        """Fetch every page or fail instead of treating incomplete data as a full history."""
        page = 1
        expected_page_count: int | None = None
        items: list[dict[str, Any]] = []
        while True:
            data = await self.request(
                "GET",
                self._endpoint(endpoint),
                headers=self.headers,
                params={"page": page, "pageSize": page_size},
            )
            if not isinstance(data, dict):
                raise UpstreamAPIError(f"Invalid Hevy response for {endpoint}")
            page_count = data.get("page_count")
            response_page = data.get("page")
            batch = data.get(items_key)
            if (
                not isinstance(page_count, int)
                or isinstance(page_count, bool)
                or page_count < 0
                or response_page != page
                or not isinstance(batch, list)
                or not all(isinstance(item, dict) for item in batch)
            ):
                raise UpstreamAPIError(f"Invalid Hevy pagination response for {endpoint}")
            if expected_page_count is None:
                expected_page_count = page_count
            elif page_count != expected_page_count:
                raise UpstreamAPIError(f"Hevy pagination changed while loading {endpoint}; retry")
            if page_count == 0 and batch:
                raise UpstreamAPIError(f"Invalid empty-page response for {endpoint}")
            items.extend(batch)
            if page >= page_count:
                return items
            page += 1

    async def get_all_workouts(self) -> list[WorkoutSession]:
        """Fetch full workout history; Hevy supports a maximum of 10 per page."""
        items = await self._get_all_pages("workouts", "workouts", 10)
        workouts = [self._parse_workout(item) for item in items]
        ids = [workout.id for workout in workouts]
        if any(not item for item in ids) or len(set(ids)) != len(ids):
            raise UpstreamAPIError("Missing or duplicate Hevy workout IDs; retry")
        return workouts

    async def get_exercise_templates(self) -> list[dict[str, Any]]:
        """Fetch Hevy's exercise templates and their muscle groups."""
        return await self._get_all_pages("exercise_templates", "exercise_templates", 100)
