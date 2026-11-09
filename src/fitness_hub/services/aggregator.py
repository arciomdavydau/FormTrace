"""Deterministic aggregation and readiness scoring engine combining telemetry from all upstreams."""

from __future__ import annotations

import asyncio
import logging
from datetime import date as dt_date
from datetime import datetime, timedelta

from fitness_hub.clients.hevy import HevyClient
from fitness_hub.clients.nutrition import NutritionAdapter
from fitness_hub.clients.wearables import WearablesClient
from fitness_hub.config import Settings, get_settings
from fitness_hub.models.biometrics import (
    BiometricSnapshot,
    DailyActivity,
    SleepMetrics,
)
from fitness_hub.models.nutrition import DailyNutritionSummary
from fitness_hub.models.readiness import (
    DailyReadinessReport,
    ReadinessScore,
    ReadinessStatus,
)
from fitness_hub.models.workouts import WorkoutSession

logger = logging.getLogger(__name__)


class FitnessAggregatorService:
    """
    Core BFF aggregator service.
    Orchestrates parallel data fetching across upstreams and computes
    deterministic, mathematical training readiness and recovery metrics.
    """

    def __init__(
        self,
        wearables_client: WearablesClient | None = None,
        hevy_client: HevyClient | None = None,
        nutrition_adapter: NutritionAdapter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.wearables = wearables_client or WearablesClient(settings=self.settings)
        self.hevy = hevy_client or HevyClient(settings=self.settings)
        self.nutrition = nutrition_adapter or NutritionAdapter(settings=self.settings)

    async def get_daily_biometrics(self, target_date: str) -> BiometricSnapshot:
        """Fetch combined activity and sleep metrics for a target date."""
        return await self.wearables.get_biometric_snapshot(target_date)

    async def get_recent_workouts(self, limit: int = 3) -> list[WorkoutSession]:
        """Fetch recent workouts from Hevy."""
        return await self.hevy.get_recent_workouts(limit=limit)

    async def get_nutrition_status(self, target_date: str) -> DailyNutritionSummary:
        """Fetch nutritional summary for a specific date."""
        return await self.nutrition.get_daily_summary(target_date)

    def _compute_readiness_score(
        self,
        sleep: SleepMetrics | None,
        activity: DailyActivity | None,
        last_workout: WorkoutSession | None,
        nutrition: DailyNutritionSummary | None,
        target_date: str,
    ) -> tuple[ReadinessScore, list[str]]:
        """
        Deterministic calculation of readiness score (0-100) and coaching notes.
        Weights:
          - Sleep: 40% (baseline 450 min / 7.5h)
          - Biometrics: 20% (step load & resting HR)
          - Workout strain: 25% (tonnage & time elapsed)
          - Nutrition: 15% (protein goal adherence)
        """
        coaching_notes: list[str] = []

        # 1. Sleep Component (40% weight) - 450 minutes baseline (7.5 hours)
        baseline_sleep_mins = 450.0
        if sleep and sleep.total_sleep_minutes > 0:
            dur_score = min(100.0, (sleep.total_sleep_minutes / baseline_sleep_mins) * 100.0)
            eff_score = sleep.sleep_efficiency_pct if sleep.sleep_efficiency_pct > 0 else 85.0
            sleep_subscore = (dur_score * 0.70) + (eff_score * 0.30)

            if sleep.total_sleep_minutes < 390:  # < 6.5 hours
                coaching_notes.append("Sub-optimal sleep (<6.5h)")
            elif sleep.total_sleep_minutes >= 450:
                coaching_notes.append("Sleep duration target met (>= 7.5h)")
        else:
            sleep_subscore = 70.0  # Sensible default if sleep data is not available yet

        # 2. Biometrics Component (20% weight) - Resting HR & Step load
        resting_hr = None
        if sleep and sleep.resting_hr_bpm:
            resting_hr = sleep.resting_hr_bpm
        elif activity and activity.resting_hr_bpm:
            resting_hr = activity.resting_hr_bpm

        bio_score = 80.0
        if resting_hr is not None:
            # Baseline is ~60 bpm. Elevating >65 indicates stress / acute fatigue
            if resting_hr > 65:
                bio_score = max(30.0, 85.0 - (resting_hr - 60) * 4.0)
                coaching_notes.append(
                    "Elevated resting heart rate detected (>5 bpm above baseline)"
                )
            elif resting_hr <= 58:
                bio_score = 95.0
                coaching_notes.append("Resting heart rate in optimal recovery zone")
            else:
                bio_score = 85.0

        if activity and activity.steps > 0:
            step_ratio = min(1.2, activity.steps / float(self.settings.target_daily_steps))
            bio_score = (bio_score * 0.7) + (min(100.0, step_ratio * 100.0) * 0.3)

        biometrics_subscore = min(100.0, max(0.0, bio_score))

        # 3. Last Workout Strain & Fatigue (25% weight)
        workout_strain_subscore = 85.0
        if last_workout:
            tonnage = last_workout.working_tonnage_kg
            # Calculate hours since last workout
            hours_elapsed = 48.0
            try:
                workout_dt = datetime.fromisoformat(last_workout.start_time.replace("Z", "+00:00"))
                target_dt = datetime.fromisoformat(target_date)
                hours_elapsed = max(
                    0.0, (target_dt - workout_dt.replace(tzinfo=None)).total_seconds() / 3600.0
                )
            except Exception:
                pass

            if tonnage > 8000:
                coaching_notes.append(
                    f"High central nervous system load from previous workout (>{tonnage:,.0f} kg working tonnage)"
                )
                workout_strain_subscore = 55.0 if hours_elapsed < 36 else 75.0
            elif tonnage > 5000:
                workout_strain_subscore = 70.0 if hours_elapsed < 24 else 85.0
            else:
                workout_strain_subscore = 90.0

            if last_workout.avg_rpe and last_workout.avg_rpe >= 8.5:
                coaching_notes.append(
                    f"High intensity recorded on previous session (avg RPE {last_workout.avg_rpe})"
                )
        else:
            workout_strain_subscore = 90.0
            coaching_notes.append(
                "No high-intensity resistance training recorded in prior 48 hours"
            )

        # 4. Nutrition Adherence (15% weight)
        target_protein = self.settings.target_protein_g
        if nutrition and nutrition.calories_kcal > 0:
            if nutrition.protein_goal_met:
                nutrition_subscore = 100.0
                coaching_notes.append(f"Protein goal achieved (>= {target_protein}g)")
            else:
                prot_ratio = (
                    nutrition.protein_g / float(target_protein) if target_protein > 0 else 1.0
                )
                nutrition_subscore = max(30.0, min(100.0, prot_ratio * 100.0))
                coaching_notes.append(f"Low protein intake (< {target_protein}g)")
        else:
            nutrition_subscore = 75.0

        # Weighted calculation
        final_numeric = int(
            round(
                (sleep_subscore * 0.40)
                + (biometrics_subscore * 0.20)
                + (workout_strain_subscore * 0.25)
                + (nutrition_subscore * 0.15)
            )
        )
        final_numeric = max(0, min(100, final_numeric))

        if final_numeric >= 80:
            status: ReadinessStatus = "OPTIMAL"
            coaching_notes.insert(0, "Optimal recovery state for heavy compound lifting")
        elif final_numeric >= 60:
            status = "MODERATE"
            coaching_notes.insert(0, "Moderate recovery. Standard working volume supported")
        else:
            status = "RECOVERY_NEEDED"
            coaching_notes.insert(
                0, "Recovery needed. Consider active recovery, deload, or extra sleep"
            )

        readiness_score = ReadinessScore(
            score=final_numeric,
            status=status,
            sleep_subscore=round(sleep_subscore, 1),
            biometrics_subscore=round(biometrics_subscore, 1),
            workout_strain_subscore=round(workout_strain_subscore, 1),
            nutrition_subscore=round(nutrition_subscore, 1),
        )

        return readiness_score, coaching_notes

    async def generate_readiness_report(self, target_date: str) -> DailyReadinessReport:
        """
        Flagship composite BFF tool:
        Concurrently queries sleep, activity, workouts, and nutrition using asyncio.gather.
        Computes deterministic readiness scoring and returns a consolidated report.
        """
        # Determine previous day date for nutrition / recovery context
        try:
            curr_dt = datetime.fromisoformat(target_date)
            prev_date = (curr_dt - timedelta(days=1)).date().isoformat()
        except Exception:
            prev_date = (dt_date.today() - timedelta(days=1)).isoformat()

        # Execute parallel fetches across all 3 upstreams
        results = await asyncio.gather(
            self.wearables.get_daily_activity(target_date),
            self.wearables.get_sleep_metrics(target_date),
            self.hevy.get_recent_workouts(limit=1),
            self.nutrition.get_daily_summary(prev_date),
            return_exceptions=True,
        )

        activity_res, sleep_res, workouts_res, nutrition_res = results

        activity: DailyActivity | None = (
            activity_res if isinstance(activity_res, DailyActivity) else None
        )
        sleep: SleepMetrics | None = sleep_res if isinstance(sleep_res, SleepMetrics) else None
        last_workout: WorkoutSession | None = (
            workouts_res[0] if isinstance(workouts_res, list) and workouts_res else None
        )
        nutrition: DailyNutritionSummary | None = (
            nutrition_res if isinstance(nutrition_res, DailyNutritionSummary) else None
        )

        biometrics = BiometricSnapshot(date=target_date, activity=activity, sleep=sleep)

        readiness_score, coaching_notes = self._compute_readiness_score(
            sleep=sleep,
            activity=activity,
            last_workout=last_workout,
            nutrition=nutrition,
            target_date=target_date,
        )

        return DailyReadinessReport(
            date=target_date,
            readiness_score=readiness_score.score,
            status=readiness_score.status,
            biometrics=biometrics,
            last_workout=last_workout,
            nutrition=nutrition,
            coaching_notes=coaching_notes,
        )
