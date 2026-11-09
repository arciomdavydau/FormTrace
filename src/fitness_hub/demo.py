"""Small, entirely fictional dataset for demos and development."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fitness_hub.clients.base import NotFoundError, UpstreamAPIError
from fitness_hub.models.workouts import ExerciseLog, ExerciseSet, SetType, WorkoutSession


class DemoHevyClient:
    """Return synthetic workouts without making any network requests."""

    async def get_all_workouts(self) -> list[WorkoutSession]:
        return [
            WorkoutSession(
                id="demo-workout-1",
                title="Demo full body A",
                start_time="2026-11-04T18:00:00Z",
                end_time="2026-11-04T19:00:00Z",
                exercises=[
                    ExerciseLog(
                        title="Demo bench press",
                        exercise_template_id="demo-bench",
                        sets=[
                            ExerciseSet(set_type=SetType.WARMUP, weight_kg=30, reps=10),
                            ExerciseSet(set_type=SetType.NORMAL, weight_kg=50, reps=8),
                            ExerciseSet(set_type=SetType.NORMAL, weight_kg=50, reps=7),
                        ],
                    ),
                    ExerciseLog(
                        title="Demo squat",
                        exercise_template_id="demo-squat",
                        sets=[
                            ExerciseSet(set_type=SetType.NORMAL, weight_kg=60, reps=8),
                            ExerciseSet(set_type=SetType.NORMAL, weight_kg=60, reps=8),
                        ],
                    ),
                ],
            ),
            WorkoutSession(
                id="demo-workout-2",
                title="Demo full body B",
                start_time="2026-11-07T18:00:00Z",
                end_time="2026-11-07T19:00:00Z",
                exercises=[
                    ExerciseLog(
                        title="Demo bench press",
                        exercise_template_id="demo-bench",
                        sets=[
                            ExerciseSet(set_type=SetType.NORMAL, weight_kg=50, reps=9),
                            ExerciseSet(set_type=SetType.FAILURE, weight_kg=50, reps=8),
                        ],
                    ),
                ],
            ),
        ]

    async def get_exercise_templates(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "demo-bench",
                "title": "Demo bench press",
                "type": "weight_reps",
                "primary_muscle_group": "chest",
                "secondary_muscle_groups": ["triceps", "shoulders"],
            },
            {
                "id": "demo-squat",
                "title": "Demo squat",
                "type": "weight_reps",
                "primary_muscle_group": "quadriceps",
                "secondary_muscle_groups": ["glutes"],
            },
        ]

    async def api_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Provide fictional read results; demo writes support preview only."""
        if method != "GET":
            raise UpstreamAPIError("Demo mode supports write previews only; no data was changed")
        params = params or {}
        page = int(params.get("page", 1))
        page_size = int(params.get("pageSize", 10))
        workouts = []
        for session in await self.get_all_workouts():
            raw = session.model_dump(mode="json")
            for exercise in raw["exercises"]:
                for recorded_set in exercise["sets"]:
                    recorded_set["type"] = recorded_set.pop("set_type")
            workouts.append(raw)
        templates = await self.get_exercise_templates()

        def paginated(name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
            return {
                "page": page,
                "page_count": (len(items) + page_size - 1) // page_size,
                name: items[(page - 1) * page_size : page * page_size],
            }

        if path == "user/info":
            return {
                "data": {
                    "id": "demo-user",
                    "name": "Demo user",
                    "is_pro": False,
                    "weight_unit": "kg",
                    "distance_unit": "kilometers",
                }
            }
        if path == "workouts/count":
            return {"workout_count": len(workouts)}
        if path == "workouts/events":
            return paginated("events", [])
        if path == "workouts":
            return paginated("workouts", workouts)
        if path == "exercise_templates":
            return paginated("exercise_templates", templates)
        if path == "routines":
            return paginated("routines", [])
        if path == "routine_folders":
            return paginated("routine_folders", [])
        if path.startswith("workouts/"):
            for workout in workouts:
                if workout["id"] == path.removeprefix("workouts/"):
                    return workout
        if path.startswith("exercise_templates/"):
            for template in templates:
                if template["id"] == path.removeprefix("exercise_templates/"):
                    return template
        if path.startswith("exercise_history/"):
            template_id = path.removeprefix("exercise_history/")
            entries: list[dict[str, Any]] = []
            for workout in workouts:
                time = datetime.fromisoformat(workout["start_time"].replace("Z", "+00:00"))
                if params.get("start_date") and time < datetime.fromisoformat(
                    str(params["start_date"]).replace("Z", "+00:00")
                ):
                    continue
                if params.get("end_date") and time > datetime.fromisoformat(
                    str(params["end_date"]).replace("Z", "+00:00")
                ):
                    continue
                for exercise in workout["exercises"]:
                    if exercise["exercise_template_id"] == template_id:
                        for recorded_set in exercise["sets"]:
                            entries.append(
                                {
                                    "workout_id": workout["id"],
                                    "workout_title": workout["title"],
                                    "workout_start_time": workout["start_time"],
                                    "workout_end_time": workout["end_time"],
                                    "exercise_template_id": template_id,
                                    "set_type": recorded_set["type"],
                                    **{
                                        k: recorded_set.get(k)
                                        for k in (
                                            "weight_kg",
                                            "reps",
                                            "distance_meters",
                                            "duration_seconds",
                                            "rpe",
                                        )
                                    },
                                }
                            )
            return {"exercise_history": entries}
        raise NotFoundError("Resource not found in the demo source", status_code=404)

    async def close(self) -> None:
        return None
