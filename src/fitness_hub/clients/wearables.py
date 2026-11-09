"""Client for Open Wearables service fetching daily activity, sleep, and heart rate telemetry."""

from __future__ import annotations

import logging
from typing import Any

from fitness_hub.clients.base import BaseAsyncClient
from fitness_hub.config import Settings, get_settings
from fitness_hub.models.biometrics import (
    BiometricSnapshot,
    DailyActivity,
    SleepMetrics,
)

logger = logging.getLogger(__name__)


class WearablesClient(BaseAsyncClient):
    """Asynchronous client communicating with Open Wearables API."""

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        super().__init__(
            base_url=cfg.open_wearables_base_url,
            timeout=cfg.request_timeout,
            max_retries=cfg.max_retries,
        )
        self.api_key = cfg.open_wearables_api_key

    @property
    def headers(self) -> dict[str, str]:
        """Headers for Open Wearables authentication."""
        hdrs: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            hdrs["X-Open-Wearables-API-Key"] = self.api_key
            hdrs["Authorization"] = f"Bearer {self.api_key}"
        return hdrs

    async def get_daily_activity(self, date: str) -> DailyActivity:
        """
        Fetch daily physical activity (steps, active calories, resting HR) for a specific date (YYYY-MM-DD).
        Hits /api/v1/activity/{date}.
        """
        data = await self.request("GET", f"/api/v1/activity/{date}", headers=self.headers)
        raw: dict[str, Any] = data if isinstance(data, dict) else {}
        if "records" in raw and isinstance(raw["records"], list) and raw["records"]:
            raw = raw["records"][0]

        hr_bpm = raw.get("resting_hr_bpm")
        if hr_bpm is None and "heart_rate" in raw and isinstance(raw["heart_rate"], dict):
            hr_bpm = raw["heart_rate"].get("resting_bpm")

        return DailyActivity(
            date=raw.get("date", date),
            steps=int(raw.get("steps", 0)),
            active_calories=int(raw.get("active_calories", raw.get("active_calories_kcal", 0))),
            resting_hr_bpm=int(hr_bpm or 60),
            distance_meters=float(raw.get("distance_meters", 0.0)),
        )

    async def get_sleep_metrics(self, date: str) -> SleepMetrics:
        """
        Fetch nightly sleep session (total sleep minutes, stages, efficiency, HRV) for a specific date.
        Hits /api/v1/sleep/{date}.
        """
        data = await self.request("GET", f"/api/v1/sleep/{date}", headers=self.headers)
        raw: dict[str, Any] = data if isinstance(data, dict) else {}
        if "records" in raw and isinstance(raw["records"], list) and raw["records"]:
            raw = raw["records"][0]

        total_mins = raw.get("total_sleep_minutes")
        if total_mins is None and "total_sleep_seconds" in raw:
            total_mins = int(raw["total_sleep_seconds"]) // 60
        elif total_mins is None and "duration_seconds" in raw:
            total_mins = int(raw["duration_seconds"]) // 60

        deep_mins = raw.get("deep_sleep_minutes")
        if deep_mins is None and "stages" in raw and isinstance(raw["stages"], dict):
            deep_mins = int(raw["stages"].get("deep_seconds", 0)) // 60

        rem_mins = raw.get("rem_sleep_minutes")
        if rem_mins is None and "stages" in raw and isinstance(raw["stages"], dict):
            rem_mins = int(raw["stages"].get("rem_seconds", 0)) // 60

        eff = raw.get("sleep_efficiency_pct")
        if eff is None:
            eff = raw.get("efficiency_percent", raw.get("efficiency", 85.0))

        return SleepMetrics(
            date=raw.get("date", date),
            total_sleep_minutes=int(total_mins or 0),
            deep_sleep_minutes=int(deep_mins or 0),
            rem_sleep_minutes=int(rem_mins or 0),
            sleep_efficiency_pct=float(eff or 0.0),
            resting_hr_bpm=raw.get("resting_hr_bpm", raw.get("resting_heart_rate")),
            hrv_sdnn_ms=raw.get("hrv_sdnn_ms", raw.get("hrv_sdnn")),
        )

    async def get_biometric_snapshot(self, date: str) -> BiometricSnapshot:
        """Fetch and combine both activity and sleep into a single biometric snapshot."""
        try:
            activity = await self.get_daily_activity(date)
        except Exception as e:
            logger.warning("Could not fetch activity for %s: %s", date, e)
            activity = None

        try:
            sleep = await self.get_sleep_metrics(date)
        except Exception as e:
            logger.warning("Could not fetch sleep for %s: %s", date, e)
            sleep = None

        return BiometricSnapshot(date=date, activity=activity, sleep=sleep)
