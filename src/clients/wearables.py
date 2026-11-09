"""Open Wearables API client for biometrics, daily activity, and sleep metrics."""

from __future__ import annotations

import logging
from typing import Any

from src.clients.base import (
    BaseAsyncHTTPClient,
    ConfigurationError,
    NotFoundError,
)
from src.config import Settings, get_settings
from src.models.biometrics import (
    BiometricsSummary,
    DailyActivity,
    HeartRateInfo,
    SleepSession,
    SleepStages,
)

logger = logging.getLogger(__name__)


class OpenWearablesClient(BaseAsyncHTTPClient):
    """Client for querying the Open Wearables backend REST API."""

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        super().__init__(
            base_url=cfg.open_wearables_api_url,
            timeout=cfg.open_wearables_timeout,
            max_retries=cfg.max_retries,
            backoff_factor=cfg.backoff_factor,
        )
        self.api_key = cfg.open_wearables_api_key.get_secret_value()
        self.default_user_id = cfg.open_wearables_default_user_id
        self._cached_user_id: str | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Headers required for Open Wearables authentication."""
        hdrs: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            hdrs["X-Open-Wearables-API-Key"] = self.api_key
        return hdrs

    def _ensure_configured(self) -> None:
        """Validate that the API key is configured."""
        if not self.api_key:
            raise ConfigurationError(
                "OPEN_WEARABLES_API_KEY is not configured. "
                "Please set it in your environment or .env file."
            )

    async def get_users(self, search: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """List accessible users."""
        self._ensure_configured()
        params: dict[str, Any] = {"limit": limit}
        if search:
            params["search"] = search

        resp = await self.request("GET", "/api/v1/users", headers=self.headers, params=params)
        if isinstance(resp, dict):
            return resp.get("items") or resp.get("users") or resp.get("records") or []
        if isinstance(resp, list):
            return resp
        return []

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Fetch details of a specific user."""
        self._ensure_configured()
        resp = await self.request("GET", f"/api/v1/users/{user_id}", headers=self.headers)
        if isinstance(resp, dict):
            return resp
        return {"id": user_id}

    async def resolve_user_id(self, user_id: str | None = None) -> str:
        """
        Resolve the user ID to query:
        1. Explicitly passed user_id
        2. Configured default user ID
        3. Previously resolved user ID from cache
        4. Single user auto-discovery from API key
        """
        if user_id:
            return user_id

        if self.default_user_id:
            return self.default_user_id

        if self._cached_user_id:
            return self._cached_user_id

        users = await self.get_users(limit=2)
        if not users:
            raise NotFoundError("No Open Wearables users found for the configured API key.")

        if len(users) == 1:
            discovered_id = str(users[0].get("id"))
            self._cached_user_id = discovered_id
            return discovered_id

        raise ConfigurationError(
            "Multiple users detected. Please supply an explicit user_id or set OPEN_WEARABLES_DEFAULT_USER_ID."
        )

    async def get_activity_summaries(
        self,
        start_date: str,
        end_date: str,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[DailyActivity]:
        """
        Fetch daily activity records (steps, calories, heart rate) for a date range.
        """
        self._ensure_configured()
        resolved_id = await self.resolve_user_id(user_id)
        endpoint = f"/api/v1/users/{resolved_id}/summaries/activity"
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
        }

        data = await self.request("GET", endpoint, headers=self.headers, params=params)
        records_raw: list[dict[str, Any]] = []
        if isinstance(data, dict):
            records_raw = data.get("records") or data.get("items") or []
        elif isinstance(data, list):
            records_raw = data

        activities: list[DailyActivity] = []
        for item in records_raw:
            hr_data = item.get("heart_rate") or {}
            heart_rate = HeartRateInfo(
                resting_bpm=hr_data.get("resting_bpm") or item.get("resting_heart_rate"),
                avg_bpm=hr_data.get("avg_bpm") or item.get("avg_heart_rate"),
                min_bpm=hr_data.get("min_bpm") or item.get("min_heart_rate"),
                max_bpm=hr_data.get("max_bpm") or item.get("max_heart_rate"),
            )
            activity = DailyActivity(
                date=item.get("date", ""),
                steps=item.get("steps", 0),
                distance_meters=float(item.get("distance_meters", 0.0) or 0.0),
                active_calories_kcal=float(item.get("active_calories_kcal", 0.0) or 0.0),
                total_calories_kcal=float(
                    item.get("total_calories_kcal", 0.0) or item.get("calories", 0.0) or 0.0
                ),
                active_minutes=int(item.get("active_minutes", 0) or 0),
                heart_rate=heart_rate,
                intensity_minutes=item.get("intensity_minutes", {}) or {},
            )
            activities.append(activity)

        return sorted(activities, key=lambda a: a.date)

    async def get_sleep_summaries(
        self,
        start_date: str,
        end_date: str,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[SleepSession]:
        """
        Fetch sleep sessions and stage breakdowns for a date range.
        """
        self._ensure_configured()
        resolved_id = await self.resolve_user_id(user_id)
        endpoint = f"/api/v1/users/{resolved_id}/summaries/sleep"
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
        }

        data = await self.request("GET", endpoint, headers=self.headers, params=params)
        records_raw: list[dict[str, Any]] = []
        if isinstance(data, dict):
            records_raw = data.get("records") or data.get("items") or []
        elif isinstance(data, list):
            records_raw = data

        sleep_sessions: list[SleepSession] = []
        for item in records_raw:
            stages_raw = item.get("stages") or {}
            deep_sec = stages_raw.get("deep_seconds") or item.get("deep_sleep_seconds") or 0
            rem_sec = stages_raw.get("rem_seconds") or item.get("rem_sleep_seconds") or 0
            light_sec = stages_raw.get("light_seconds") or item.get("light_sleep_seconds") or 0
            awake_sec = stages_raw.get("awake_seconds") or item.get("awake_time_seconds") or 0

            stages = SleepStages(
                deep_seconds=int(deep_sec),
                rem_seconds=int(rem_sec),
                light_seconds=int(light_sec),
                awake_seconds=int(awake_sec),
            )

            total_sec = (
                item.get("total_sleep_seconds")
                or item.get("duration_seconds")
                or (deep_sec + rem_sec + light_sec)
            )

            session = SleepSession(
                session_id=item.get("id") or item.get("session_id"),
                date=item.get("date", ""),
                start_time=item.get("start_time"),
                end_time=item.get("end_time"),
                total_sleep_seconds=int(total_sec or 0),
                time_in_bed_seconds=item.get("time_in_bed_seconds"),
                efficiency_percent=item.get("efficiency_percent") or item.get("efficiency"),
                stages=stages,
                resting_heart_rate=item.get("resting_heart_rate"),
                hrv_sdnn=item.get("hrv_sdnn") or item.get("sdnn"),
                hrv_rmssd=item.get("hrv_rmssd") or item.get("rmssd"),
                sleep_score=item.get("sleep_score") or item.get("score"),
            )
            sleep_sessions.append(session)

        return sorted(sleep_sessions, key=lambda s: s.date)

    async def get_data_sources(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """List connected data sources for a user."""
        self._ensure_configured()
        resolved_id = await self.resolve_user_id(user_id)
        resp = await self.request(
            "GET",
            f"/api/v1/users/{resolved_id}/data-sources",
            headers=self.headers,
        )
        if isinstance(resp, dict):
            return resp.get("items") or resp.get("data_sources") or []
        if isinstance(resp, list):
            return resp
        return []

    async def get_sdnn_stability(
        self,
        reference_date: str,
        user_id: str | None = None,
        data_source_id: str | None = None,
        timezone: str = "UTC",
    ) -> dict[str, Any]:
        """Fetch descriptive SDNN stability and baseline stats."""
        self._ensure_configured()
        resolved_id = await self.resolve_user_id(user_id)

        # If data_source_id is not given, try to find the first valid source
        source_id = data_source_id
        if not source_id:
            sources = await self.get_data_sources(resolved_id)
            if sources:
                source_id = str(sources[0].get("id"))

        params: dict[str, Any] = {
            "reference_date": reference_date,
            "timezone": timezone,
        }
        if source_id:
            params["data_source_id"] = source_id

        resp = await self.request(
            "GET",
            f"/api/v1/users/{resolved_id}/sdnn-stability",
            headers=self.headers,
            params=params,
        )
        if isinstance(resp, dict):
            return resp
        return {}

    async def get_biometrics_summary(
        self,
        start_date: str,
        end_date: str,
        user_id: str | None = None,
    ) -> BiometricsSummary:
        """Fetch and aggregate both daily activity and sleep metrics for a period."""
        activities = await self.get_activity_summaries(start_date, end_date, user_id=user_id)
        sleeps = await self.get_sleep_summaries(start_date, end_date, user_id=user_id)

        days_count = len(activities) or len(sleeps) or 1
        avg_steps = sum(a.steps for a in activities) / len(activities) if activities else 0.0
        avg_cal = (
            sum(a.active_calories_kcal for a in activities) / len(activities) if activities else 0.0
        )
        avg_sleep_hrs = sum(s.duration_hours for s in sleeps) / len(sleeps) if sleeps else 0.0

        rhr_vals = [s.resting_heart_rate for s in sleeps if s.resting_heart_rate is not None] or [
            a.heart_rate.resting_bpm for a in activities if a.heart_rate.resting_bpm is not None
        ]
        avg_rhr = round(sum(rhr_vals) / len(rhr_vals), 1) if rhr_vals else None

        return BiometricsSummary(
            start_date=start_date,
            end_date=end_date,
            days_count=days_count,
            avg_daily_steps=round(avg_steps, 1),
            avg_active_calories=round(avg_cal, 1),
            avg_sleep_hours=round(avg_sleep_hrs, 2),
            avg_resting_hr=avg_rhr,
            daily_activities=activities,
            sleep_sessions=sleeps,
        )
