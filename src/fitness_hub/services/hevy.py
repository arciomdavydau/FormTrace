"""Hevy API operations, kept separate from the MCP transport."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from fitness_hub.models.hevy_inputs import RoutineCreateInput, WorkoutCreateInput
from fitness_hub.services.training import TrainingService


def resource_id(value: str) -> str:
    """Allow IDs, not arbitrary paths, in the provider URL."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Invalid Hevy resource ID")
    return value


def page_params(page: int, page_size: int, maximum: int) -> dict[str, int]:
    if page < 1 or page_size < 1 or page_size > maximum:
        raise ValueError(f"page must be >= 1 and page_size must be between 1 and {maximum}")
    return {"page": page, "pageSize": page_size}


def aware_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            raise ValueError("Timestamp needs an offset")
        return parsed
    except ValueError as exc:
        raise ValueError("Use an ISO 8601 timestamp with a timezone offset") from exc


class HevyOperations:
    def __init__(self, training: TrainingService) -> None:
        self.training = training

    def _source_info(self) -> dict[str, str]:
        return {"provider": self.training.provider, "fetched_at": datetime.now(UTC).isoformat()}

    async def read(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        result = await self.training.source.api_request("GET", path, params=params)
        return {"source": self._source_info(), "data": result}

    async def write(
        self, method: str, path: str, wrapper: str, payload: BaseModel, *, dry_run: bool
    ) -> dict[str, Any]:
        body = {wrapper: payload.model_dump(mode="json", exclude_unset=True)}
        # The Hevy workout API defaults privacy to public when omitted. Include our
        # explicit private default even when callers leave it out.
        if wrapper == "workout":
            if not isinstance(payload, WorkoutCreateInput):
                raise TypeError("Workout payload required")
            body[wrapper]["is_private"] = payload.is_private
        if wrapper == "routine" and isinstance(payload, RoutineCreateInput):
            body[wrapper]["folder_id"] = payload.folder_id
        if wrapper in {"workout", "routine"}:
            for exercise in body[wrapper].get("exercises", []):
                for recorded_set in exercise.get("sets", []):
                    recorded_set.setdefault("type", "normal")
        if dry_run:
            return {
                "dry_run": True,
                "provider": self.training.provider,
                "operation": method,
                "resource": path,
                "payload": body,
                "message": "Preview only; no data was written to Hevy.",
            }
        try:
            result = await self.training.source.api_request(method, path, body=body)
        finally:
            # A timed-out write may have been applied. Never keep the old snapshot.
            await self.training.invalidate()
        return {"dry_run": False, "source": self._source_info(), "data": result}
