"""Small, entirely fictional dataset for demos and development."""

from __future__ import annotations

from typing import Any

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

    async def close(self) -> None:
        return None
