"""Tests for WearablesClient using respx HTTP mocking against Open Wearables API."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from fitness_hub.clients.base import (
    AuthenticationError,
    NotFoundError,
)
from fitness_hub.clients.wearables import WearablesClient


@pytest.mark.asyncio
@respx.mock
async def test_wearables_get_daily_activity(
    wearables_client: WearablesClient,
    sample_wearables_activity_payload: dict[str, Any],
) -> None:
    """Verify deserialization of daily activity data from /api/v1/activity/{date}."""
    respx.get("http://localhost:8080/api/v1/activity/2026-11-09").mock(
        return_value=httpx.Response(200, json=sample_wearables_activity_payload)
    )

    activity = await wearables_client.get_daily_activity("2026-11-09")
    assert activity.date == "2026-11-09"
    assert activity.steps == 10450
    assert activity.active_calories == 520
    assert activity.resting_hr_bpm == 56
    assert activity.distance_meters == 7820.5


@pytest.mark.asyncio
@respx.mock
async def test_wearables_get_sleep_metrics(
    wearables_client: WearablesClient,
    sample_wearables_sleep_payload: dict[str, Any],
) -> None:
    """Verify deserialization of sleep metrics from /api/v1/sleep/{date}."""
    respx.get("http://localhost:8080/api/v1/sleep/2026-11-09").mock(
        return_value=httpx.Response(200, json=sample_wearables_sleep_payload)
    )

    sleep = await wearables_client.get_sleep_metrics("2026-11-09")
    assert sleep.date == "2026-11-09"
    assert sleep.total_sleep_minutes == 465
    assert sleep.duration_hours == 7.75
    assert sleep.deep_sleep_minutes == 105
    assert sleep.rem_sleep_minutes == 120
    assert sleep.sleep_efficiency_pct == 92.5
    assert sleep.resting_hr_bpm == 54
    assert sleep.hrv_sdnn_ms == 68.2


@pytest.mark.asyncio
@respx.mock
async def test_wearables_get_biometric_snapshot(
    wearables_client: WearablesClient,
    sample_wearables_activity_payload: dict[str, Any],
    sample_wearables_sleep_payload: dict[str, Any],
) -> None:
    """Verify aggregated BiometricSnapshot retrieves both activity and sleep concurrently."""
    respx.get("http://localhost:8080/api/v1/activity/2026-11-09").mock(
        return_value=httpx.Response(200, json=sample_wearables_activity_payload)
    )
    respx.get("http://localhost:8080/api/v1/sleep/2026-11-09").mock(
        return_value=httpx.Response(200, json=sample_wearables_sleep_payload)
    )

    snapshot = await wearables_client.get_biometric_snapshot("2026-11-09")
    assert snapshot.date == "2026-11-09"
    assert snapshot.activity is not None
    assert snapshot.activity.steps == 10450
    assert snapshot.sleep is not None
    assert snapshot.sleep.total_sleep_minutes == 465


@pytest.mark.asyncio
@respx.mock
async def test_wearables_auth_error(wearables_client: WearablesClient) -> None:
    """Verify AuthenticationError is raised on 401."""
    respx.get("http://localhost:8080/api/v1/activity/2026-11-09").mock(
        return_value=httpx.Response(401, json={"error": "Invalid API key"})
    )
    with pytest.raises(AuthenticationError):
        await wearables_client.get_daily_activity("2026-11-09")


@pytest.mark.asyncio
@respx.mock
async def test_wearables_not_found_error(wearables_client: WearablesClient) -> None:
    """Verify NotFoundError is raised on 404."""
    respx.get("http://localhost:8080/api/v1/activity/2026-11-09").mock(
        return_value=httpx.Response(404, json={"error": "Date not found"})
    )
    with pytest.raises(NotFoundError):
        await wearables_client.get_daily_activity("2026-11-09")


@pytest.mark.asyncio
@respx.mock
async def test_wearables_retry_on_rate_limit(wearables_client: WearablesClient) -> None:
    """Verify automatic retry with backoff on 429."""
    route = respx.get("http://localhost:8080/api/v1/activity/2026-11-09")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "Rate limit exceeded"}),
        httpx.Response(
            200,
            json={
                "date": "2026-11-09",
                "steps": 7500,
                "active_calories": 300,
                "resting_hr_bpm": 62,
            },
        ),
    ]

    activity = await wearables_client.get_daily_activity("2026-11-09")
    assert activity.steps == 7500
    assert route.call_count == 2
