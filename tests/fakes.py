"""Test-only training source backed by fictional Hevy fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fitness_hub.clients.hevy import HevyClient
from fitness_hub.config import Settings
from fitness_hub.models.workouts import WorkoutSession

_FIXTURES = Path(__file__).parent / "fixtures" / "hevy"


class FakeTrainingSource:
    async def get_all_workouts(self) -> list[WorkoutSession]:
        payload = json.loads((_FIXTURES / "analytics_workouts_page.json").read_text())
        parser = HevyClient(Settings(_env_file=None))
        return [parser._parse_workout(item) for item in payload["workouts"]]

    async def get_exercise_templates(self) -> list[dict[str, Any]]:
        payload = json.loads((_FIXTURES / "analytics_exercise_templates_page.json").read_text())
        return payload["exercise_templates"]  # type: ignore[no-any-return]

    async def api_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise AssertionError(f"Unexpected request: {method} {path}")

    async def close(self) -> None:
        return None
