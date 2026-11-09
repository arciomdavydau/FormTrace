"""MCP tools for querying wearable biometrics, daily activity, and sleep metrics."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from src.clients.wearables import OpenWearablesClient

logger = logging.getLogger(__name__)

biometrics_router = FastMCP(name="Biometrics Tools")
_client: OpenWearablesClient | None = None


def get_wearables_client() -> OpenWearablesClient:
    """Get or instantiate singleton OpenWearablesClient."""
    global _client
    if _client is None:
        _client = OpenWearablesClient()
    return _client


def set_wearables_client(client: OpenWearablesClient | None) -> None:
    """Override the client (useful for dependency injection in tests)."""
    global _client
    _client = client


@biometrics_router.tool
async def get_biometrics_users(
    limit: int = 20,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """
    List available users accessible via Open Wearables API key.

    Use this tool to find user IDs if multiple users exist or to inspect user profiles.
    """
    client = get_wearables_client()
    return await client.get_users(search=search, limit=limit)


@biometrics_router.tool
async def get_daily_activity(
    start_date: str,
    end_date: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Query daily physical activity metrics (steps, active calories, total calories, active minutes, heart rate).

    Args:
        start_date: Start date in YYYY-MM-DD format (e.g. "2026-11-01")
        end_date: End date in YYYY-MM-DD format (e.g. "2026-11-08")
        user_id: Optional UUID of the user. If omitted, default or single discovered user is used.
    """
    client = get_wearables_client()
    activities = await client.get_activity_summaries(start_date, end_date, user_id=user_id)

    records = [a.model_dump() for a in activities]
    total_steps = sum(a.steps for a in activities)
    avg_steps = round(total_steps / len(activities), 1) if activities else 0.0
    total_active_cals = round(sum(a.active_calories_kcal for a in activities), 1)

    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "days_count": len(activities),
        "total_steps": total_steps,
        "avg_daily_steps": avg_steps,
        "total_active_calories_kcal": total_active_cals,
        "records": records,
    }


@biometrics_router.tool
async def get_sleep_data(
    start_date: str,
    end_date: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Query nightly sleep metrics (duration, efficiency %, sleep stages, resting HR, HRV).

    Args:
        start_date: Start date in YYYY-MM-DD format (e.g. "2026-11-01")
        end_date: End date in YYYY-MM-DD format (e.g. "2026-11-08")
        user_id: Optional UUID of the user.
    """
    client = get_wearables_client()
    sessions = await client.get_sleep_summaries(start_date, end_date, user_id=user_id)

    records = [s.model_dump() for s in sessions]
    avg_sleep_hrs = (
        round(sum(s.duration_hours for s in sessions) / len(sessions), 2) if sessions else 0.0
    )
    efficiencies = [s.efficiency_percent for s in sessions if s.efficiency_percent is not None]
    avg_efficiency = round(sum(efficiencies) / len(efficiencies), 1) if efficiencies else None

    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "total_sessions": len(sessions),
        "avg_sleep_hours": avg_sleep_hrs,
        "avg_efficiency_percent": avg_efficiency,
        "sessions": records,
    }


@biometrics_router.tool
async def get_biometrics_summary(
    start_date: str,
    end_date: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Retrieve comprehensive aggregated biometrics (steps, active calories, sleep, resting HR).

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        user_id: Optional user UUID
    """
    client = get_wearables_client()
    summary = await client.get_biometrics_summary(start_date, end_date, user_id=user_id)
    return summary.model_dump()


@biometrics_router.tool
async def get_hrv_stability(
    reference_date: str,
    user_id: str | None = None,
    data_source_id: str | None = None,
) -> dict[str, Any]:
    """
    Get heart rate variability (SDNN) stability and descriptive baseline data.

    Args:
        reference_date: Anchor date (YYYY-MM-DD)
        user_id: Optional user UUID
        data_source_id: Optional hardware device source UUID
    """
    client = get_wearables_client()
    return await client.get_sdnn_stability(
        reference_date=reference_date,
        user_id=user_id,
        data_source_id=data_source_id,
    )
