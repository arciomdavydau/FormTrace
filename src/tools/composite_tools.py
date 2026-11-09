"""Composite MCP tools combining biometrics, Hevy workouts, and nutrition for holistic readiness and workload analysis."""

from __future__ import annotations

import logging
from datetime import date as dt_date
from datetime import datetime, timedelta
from typing import Any

from fastmcp import FastMCP

from src.tools.biometrics_tools import get_wearables_client
from src.tools.nutrition_tools import get_nutrition_client
from src.tools.workout_tools import get_hevy_client

logger = logging.getLogger(__name__)

composite_router = FastMCP(name="Composite Analysis Tools")


def _get_target_date(date_str: str | None) -> str:
    """Return target date string or today's ISO date."""
    if date_str:
        return date_str
    return dt_date.today().isoformat()


@composite_router.tool
async def calculate_readiness_score(
    target_date: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Compute daily holistic readiness score (0-100) combining sleep, heart rate metrics,
    prior day workout strain, and energy availability.

    Args:
        target_date: Date to evaluate in YYYY-MM-DD format (defaults to today)
        user_id: Optional user UUID for wearable data
    """
    check_date = _get_target_date(target_date)
    ref_dt = datetime.fromisoformat(check_date)
    start_history = (ref_dt - timedelta(days=7)).date().isoformat()

    wearables = get_wearables_client()
    hevy = get_hevy_client()
    nutrition = get_nutrition_client()

    # 1. Fetch Sleep Data
    sleep_score_val = 70.0
    sleep_duration_hours = 0.0
    sleep_efficiency = 0.0
    resting_hr: int | None = None
    baseline_resting_hr: float | None = None
    hrv_sdnn: float | None = None

    try:
        sleep_sessions = await wearables.get_sleep_summaries(
            start_date=start_history,
            end_date=check_date,
            user_id=user_id,
        )
        if sleep_sessions:
            recent_sleep = sleep_sessions[-1]
            sleep_duration_hours = recent_sleep.duration_hours
            sleep_efficiency = recent_sleep.efficiency_percent or 85.0
            resting_hr = recent_sleep.resting_heart_rate
            hrv_sdnn = recent_sleep.hrv_sdnn

            # Calculate baseline resting HR over prior week
            prior_rhrs = [
                s.resting_heart_rate
                for s in sleep_sessions[:-1]
                if s.resting_heart_rate is not None
            ]
            if prior_rhrs:
                baseline_resting_hr = sum(prior_rhrs) / len(prior_rhrs)

            # Score sleep (ideal 7.5 - 9.0 hours, efficiency >= 85%)
            dur_score = min(100.0, (sleep_duration_hours / 8.0) * 100.0)
            eff_score = min(100.0, sleep_efficiency)
            sleep_score_val = (dur_score * 0.6) + (eff_score * 0.4)
    except Exception as e:
        logger.warning("Could not fetch wearable sleep data: %s", e)

    # 2. Cardiovascular Autonomic Score
    cardio_score_val = 75.0
    if resting_hr is not None and baseline_resting_hr is not None:
        hr_diff = resting_hr - baseline_resting_hr
        # If RHR elevated by >3 bpm, deduct points; if lower or equal, boost score
        if hr_diff > 0:
            cardio_score_val = max(30.0, 80.0 - (hr_diff * 5.0))
        else:
            cardio_score_val = min(100.0, 85.0 + abs(hr_diff) * 3.0)

    # 3. Prior Workload Strain (Hevy)
    strain_penalty = 0.0
    recent_tonnage = 0.0
    recent_rpe = None
    try:
        yesterday_str = (ref_dt - timedelta(days=1)).date().isoformat()
        workouts = await hevy.get_workouts(page=1, page_size=5, since=yesterday_str)
        if workouts:
            recent_tonnage = sum(w.total_tonnage_kg for w in workouts)
            rpes = [w.avg_rpe for w in workouts if w.avg_rpe is not None]
            recent_rpe = sum(rpes) / len(rpes) if rpes else None

            # High tonnage (>12,000 kg) or high RPE (>8.5) induces acute fatigue
            if recent_tonnage > 12000 or (recent_rpe and recent_rpe >= 8.5):
                strain_penalty = 15.0
            elif recent_tonnage > 6000 or (recent_rpe and recent_rpe >= 7.5):
                strain_penalty = 8.0
    except Exception as e:
        logger.warning("Could not fetch Hevy workout data: %s", e)

    # 4. Energy Availability (Nutrition)
    nutrition_score_val = 80.0
    try:
        prev_date = (ref_dt - timedelta(days=1)).date().isoformat()
        nutr_log = await nutrition.get_daily_log(prev_date)
        if nutr_log.targets and nutr_log.total_calories > 0:
            cal_ratio = nutr_log.total_calories / nutr_log.targets.calories
            if cal_ratio < 0.70:
                nutrition_score_val = 60.0  # Excessive deficit impairs recovery
            elif 0.85 <= cal_ratio <= 1.15:
                nutrition_score_val = 95.0
    except Exception as e:
        logger.warning("Could not fetch nutrition data: %s", e)

    # Composite Readiness calculation:
    # 40% Sleep + 30% Cardio/HRV + 20% Recovery from Strain + 10% Nutrition
    workload_recovery_score = max(20.0, 100.0 - (strain_penalty * 3.0))
    final_score = (
        (sleep_score_val * 0.40)
        + (cardio_score_val * 0.30)
        + (workload_recovery_score * 0.20)
        + (nutrition_score_val * 0.10)
    )
    final_score = round(max(0.0, min(100.0, final_score)), 1)

    # Category and Recommendations
    if final_score >= 85:
        category = "Optimal"
        recommendation = "Full physiological recovery. Primed for high intensity, PR attempts, or heavy compound volume."
    elif final_score >= 70:
        category = "Good"
        recommendation = "Sufficient recovery for normal scheduled training. Maintain standard working sets and target RPE 7-8."
    elif final_score >= 50:
        category = "Moderate"
        recommendation = "Mild accumulated fatigue detected. Consider moderating volume, avoiding failure sets, or doing technical work."
    else:
        category = "Low / Recovery Advised"
        recommendation = "Elevated systemic strain or sleep deficit. Recommended active recovery, mobility, or complete rest day."

    return {
        "date": check_date,
        "readiness_score": final_score,
        "category": category,
        "components": {
            "sleep_score": round(sleep_score_val, 1),
            "sleep_duration_hours": sleep_duration_hours,
            "sleep_efficiency_pct": sleep_efficiency,
            "cardio_recovery_score": round(cardio_score_val, 1),
            "resting_heart_rate": resting_hr,
            "baseline_resting_hr": round(baseline_resting_hr, 1) if baseline_resting_hr else None,
            "hrv_sdnn_ms": hrv_sdnn,
            "workload_recovery_score": round(workload_recovery_score, 1),
            "recent_workout_tonnage_kg": recent_tonnage,
            "recent_workout_avg_rpe": round(recent_rpe, 1) if recent_rpe else None,
            "nutrition_score": round(nutrition_score_val, 1),
        },
        "recommendation": recommendation,
    }


@composite_router.tool
async def calculate_energy_balance(
    date: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Calculate daily energy deficit or surplus comparing wearable Total Daily Energy Expenditure (TDEE)
    against logged nutritional calorie and macronutrient intake.

    Args:
        date: Target date in YYYY-MM-DD format
        user_id: Optional user UUID for wearable metrics
    """
    wearables = get_wearables_client()
    nutrition = get_nutrition_client()

    # 1. Fetch Wearables Energy Expenditure
    expenditure_kcal = 2200.0  # Sensible default if wearable data unavailable
    active_cals = 0.0
    steps = 0
    wearable_found = False

    try:
        activities = await wearables.get_activity_summaries(
            start_date=date,
            end_date=date,
            user_id=user_id,
        )
        if activities:
            wearable_found = True
            act = activities[0]
            steps = act.steps
            active_cals = act.active_calories_kcal
            if act.total_calories_kcal > 0:
                expenditure_kcal = act.total_calories_kcal
            else:
                # Approximate BMR (~1800 kcal) + active calories
                expenditure_kcal = 1800.0 + active_cals
    except Exception as e:
        logger.warning("Could not fetch activity calories for %s: %s", date, e)

    # 2. Fetch Nutrition Intake
    nutr_log = await nutrition.get_daily_log(date)
    intake_kcal = nutr_log.total_calories
    protein_g = nutr_log.total_protein_g
    carbs_g = nutr_log.total_carbs_g
    fat_g = nutr_log.total_fat_g

    net_kcal = round(intake_kcal - expenditure_kcal, 1)
    if net_kcal < -100:
        status = "Deficit"
    elif net_kcal > 100:
        status = "Surplus"
    else:
        status = "Maintenance"

    deficit_percentage = (
        round((net_kcal / expenditure_kcal) * 100, 1) if expenditure_kcal > 0 else 0.0
    )

    # Guidance
    if status == "Deficit":
        if abs(net_kcal) > 800:
            advice = (
                "High caloric deficit (>800 kcal). Ensure high protein intake (>=2.0g/kg) "
                "to prevent lean muscle loss during heavy training phases."
            )
        else:
            advice = "Moderate caloric deficit optimal for sustainable fat loss while maintaining strength."
    elif status == "Surplus":
        advice = "Caloric surplus provides sufficient energy for muscle hypertrophy and neuromuscular recovery."
    else:
        advice = "Energy intake matches expenditure (maintenance). Ideal for strength maintenance or body recomposition."

    return {
        "date": date,
        "energy_status": status,
        "intake_calories_kcal": intake_kcal,
        "expenditure_calories_kcal": round(expenditure_kcal, 1),
        "net_balance_kcal": net_kcal,
        "net_percentage": deficit_percentage,
        "macronutrients": {
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "fiber_g": nutr_log.total_fiber_g,
        },
        "activity_metrics": {
            "steps": steps,
            "active_calories_kcal": active_cals,
            "wearable_data_synced": wearable_found,
        },
        "dietary_guidance": advice,
    }


@composite_router.tool
async def analyze_recovery_vs_workload(
    days: int = 7,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Analyze cumulative training volume (tonnage, sets) against physiological recovery (sleep, resting HR)
    over a 7 to 14 day period to monitor overtraining risk and adaptation.

    Args:
        days: Number of days to analyze (default: 7, max: 30)
        user_id: Optional user UUID
    """
    days = max(3, min(30, days))
    today_dt = dt_date.today()
    start_dt = today_dt - timedelta(days=days)
    start_date = start_dt.isoformat()
    end_date = today_dt.isoformat()

    wearables = get_wearables_client()
    hevy = get_hevy_client()

    # 1. Training Workload
    total_tonnage = 0.0
    total_working_sets = 0
    workout_count = 0
    avg_rpe = None
    try:
        summary = await hevy.get_workout_summary(page_size=20, since=start_date)
        workout_count = summary.total_workouts
        total_tonnage = summary.total_tonnage_kg
        total_working_sets = summary.total_working_sets
        avg_rpe = summary.avg_workout_rpe
    except Exception as e:
        logger.warning("Could not fetch workouts for workload analysis: %s", e)

    # 2. Recovery Capacity (Sleep & Heart Rate)
    avg_sleep_hrs = 7.5
    avg_sleep_eff = 85.0
    resting_hr_trend = "stable"
    try:
        sleep_data = await wearables.get_sleep_summaries(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
        )
        if sleep_data:
            avg_sleep_hrs = round(sum(s.duration_hours for s in sleep_data) / len(sleep_data), 2)
            effs = [s.efficiency_percent for s in sleep_data if s.efficiency_percent is not None]
            if effs:
                avg_sleep_eff = round(sum(effs) / len(effs), 1)

            # Check resting HR trend
            rhrs = [s.resting_heart_rate for s in sleep_data if s.resting_heart_rate is not None]
            if len(rhrs) >= 4:
                first_half = sum(rhrs[: len(rhrs) // 2]) / (len(rhrs) // 2)
                second_half = sum(rhrs[len(rhrs) // 2 :]) / (len(rhrs) - len(rhrs) // 2)
                if second_half - first_half >= 3.0:
                    resting_hr_trend = "increasing (fatigue warning)"
                elif first_half - second_half >= 2.0:
                    resting_hr_trend = "decreasing (positive adaptation)"
    except Exception as e:
        logger.warning("Could not fetch sleep data for recovery analysis: %s", e)

    # 3. Workload to Recovery Ratio Evaluation
    # High volume benchmark: >30,000 kg or >60 working sets per week
    high_volume = total_tonnage > 30000 or total_working_sets > 60
    low_recovery = avg_sleep_hrs < 6.8 or avg_sleep_eff < 80.0

    if high_volume and low_recovery:
        status = "Overreaching / Overtraining Risk"
        advice = (
            "High training volume paired with insufficient sleep recovery. "
            "Recommend inserting a deload session or prioritizing 8+ hours of sleep."
        )
    elif high_volume and not low_recovery:
        status = "Optimal Progressive Overload"
        advice = "High training stimulus supported by strong recovery. Excellent environment for hypertrophy and strength gains."
    elif not high_volume and low_recovery:
        status = "Under-recovered"
        advice = "Training load is moderate, but recovery metrics (sleep) are low. Optimize sleep hygiene before raising intensity."
    else:
        status = "Balanced Maintenance / Deload"
        advice = "Workload and recovery are in equilibrium. Well positioned for upcoming training cycle progression."

    return {
        "period": {"days": days, "start_date": start_date, "end_date": end_date},
        "workload_metrics": {
            "workouts_completed": workout_count,
            "total_tonnage_kg": total_tonnage,
            "total_working_sets": total_working_sets,
            "avg_rpe": avg_rpe,
            "avg_tonnage_per_workout_kg": (
                round(total_tonnage / workout_count, 1) if workout_count else 0.0
            ),
        },
        "recovery_metrics": {
            "avg_sleep_hours": avg_sleep_hrs,
            "avg_sleep_efficiency_pct": avg_sleep_eff,
            "resting_heart_rate_trend": resting_hr_trend,
        },
        "synthesis": {
            "workload_recovery_status": status,
            "assessment": advice,
        },
    }
