"""Unit tests for OpenWearablesClient with respx HTTP mocking."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from pydantic import SecretStr

from src.clients.base import AuthenticationError, ConfigurationError, NotFoundError
from src.clients.wearables import OpenWearablesClient
from src.config import Settings


@pytest.mark.asyncio
async def test_wearables_client_unconfigured() -> None:
    """Client should raise ConfigurationError when no API key is provided."""
    unconfigured_settings = Settings(
        open_wearables_api_key=SecretStr(""),
        open_wearables_api_url="https://wearables.test",
    )
    client = OpenWearablesClient(settings=unconfigured_settings)
    with pytest.raises(ConfigurationError):
        await client.get_users()


@pytest.mark.asyncio
@respx.mock
async def test_wearables_client_auth_error(wearables_client: OpenWearablesClient) -> None:
    """Client should raise AuthenticationError on 401 response."""
    respx.get("https://test-wearables.local/api/v1/users").mock(
        return_value=httpx.Response(401, json={"detail": "Invalid API key"})
    )
    with pytest.raises(AuthenticationError):
        await wearables_client.get_users()


@pytest.mark.asyncio
@respx.mock
async def test_wearables_client_not_found(wearables_client: OpenWearablesClient) -> None:
    """Client should raise NotFoundError on 404 response."""
    respx.get("https://test-wearables.local/api/v1/users/nonexistent").mock(
        return_value=httpx.Response(404, json={"detail": "User not found"})
    )
    with pytest.raises(NotFoundError):
        await wearables_client.get_user("nonexistent")


@pytest.mark.asyncio
@respx.mock
async def test_wearables_client_get_users(wearables_client: OpenWearablesClient) -> None:
    """Test successful retrieval of user accounts."""
    respx.get("https://test-wearables.local/api/v1/users").mock(
        return_value=httpx.Response(
            200,
            json={"items": [{"id": "user-1", "first_name": "Alice", "email": "alice@test.com"}]},
        )
    )

    users = await wearables_client.get_users(search="Alice")
    assert len(users) == 1
    assert users[0]["id"] == "user-1"
    assert users[0]["first_name"] == "Alice"


@pytest.mark.asyncio
@respx.mock
async def test_wearables_client_resolve_user_id(mock_settings: Settings) -> None:
    """Test user ID resolution priority."""
    # 1. Explicit user_id wins
    client = OpenWearablesClient(settings=mock_settings)
    assert await client.resolve_user_id("explicit-id") == "explicit-id"

    # 2. Configured default user_id is used
    assert await client.resolve_user_id() == "user-uuid-default-1"

    # 3. Auto-discovery when default_user_id is None and single user exists
    settings_no_default = Settings(
        open_wearables_api_url="https://test-wearables.local",
        open_wearables_api_key=SecretStr("mock-key"),
        open_wearables_default_user_id=None,
    )
    client_autodiscover = OpenWearablesClient(settings=settings_no_default)

    respx.get("https://test-wearables.local/api/v1/users").mock(
        return_value=httpx.Response(
            200,
            json={"items": [{"id": "discovered-single-uuid", "first_name": "Bob"}]},
        )
    )
    resolved = await client_autodiscover.resolve_user_id()
    assert resolved == "discovered-single-uuid"


@pytest.mark.asyncio
@respx.mock
async def test_wearables_get_activity_summaries(
    wearables_client: OpenWearablesClient,
    sample_activity_response: dict[str, Any],
) -> None:
    """Test activity summaries fetching and Pydantic parsing."""
    respx.get(
        "https://test-wearables.local/api/v1/users/user-uuid-default-1/summaries/activity"
    ).mock(return_value=httpx.Response(200, json=sample_activity_response))

    activities = await wearables_client.get_activity_summaries(
        start_date="2026-11-08",
        end_date="2026-11-09",
    )

    assert len(activities) == 2
    act_1 = activities[0]
    assert act_1.date == "2026-11-08"
    assert act_1.steps == 10542
    assert act_1.active_calories_kcal == 480.0
    assert act_1.total_calories_kcal == 2350.0
    assert act_1.heart_rate.resting_bpm == 52

    act_2 = activities[1]
    assert act_2.date == "2026-11-09"
    assert act_2.steps == 8400


@pytest.mark.asyncio
@respx.mock
async def test_wearables_get_sleep_summaries(
    wearables_client: OpenWearablesClient,
    sample_sleep_response: dict[str, Any],
) -> None:
    """Test sleep summaries fetching, duration, and stages parsing."""
    respx.get("https://test-wearables.local/api/v1/users/user-uuid-default-1/summaries/sleep").mock(
        return_value=httpx.Response(200, json=sample_sleep_response)
    )

    sessions = await wearables_client.get_sleep_summaries(
        start_date="2026-11-08",
        end_date="2026-11-09",
    )

    assert len(sessions) == 2
    s1 = sessions[0]
    assert s1.date == "2026-11-08"
    assert s1.duration_hours == 7.5
    assert s1.efficiency_percent == 93.5
    assert s1.resting_heart_rate == 51
    assert s1.hrv_sdnn == 64.5
    assert s1.stages.deep_hours == 1.5
    assert s1.stages.rem_hours == 1.75


@pytest.mark.asyncio
@respx.mock
async def test_wearables_get_biometrics_summary(
    wearables_client: OpenWearablesClient,
    sample_activity_response: dict[str, Any],
    sample_sleep_response: dict[str, Any],
) -> None:
    """Test aggregated biometrics calculation."""
    respx.get(
        "https://test-wearables.local/api/v1/users/user-uuid-default-1/summaries/activity"
    ).mock(return_value=httpx.Response(200, json=sample_activity_response))
    respx.get("https://test-wearables.local/api/v1/users/user-uuid-default-1/summaries/sleep").mock(
        return_value=httpx.Response(200, json=sample_sleep_response)
    )

    summary = await wearables_client.get_biometrics_summary("2026-11-08", "2026-11-09")

    assert summary.days_count == 2
    assert summary.avg_daily_steps == 9471.0  # (10542 + 8400) / 2
    assert summary.avg_active_calories == 420.0  # (480 + 360) / 2
    assert summary.avg_sleep_hours == 7.25  # (7.5 + 7.0) / 2
    assert summary.avg_resting_hr == 52.0  # (51 + 53) / 2


@pytest.mark.asyncio
@respx.mock
async def test_wearables_retry_on_rate_limit(wearables_client: OpenWearablesClient) -> None:
    """Verify that 429 triggers retry logic with backoff."""
    route = respx.get("https://test-wearables.local/api/v1/users")
    # First attempt: 429, second attempt: 200
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0.01"}, json={"detail": "Too many requests"}),
        httpx.Response(200, json={"items": [{"id": "user-retried"}]}),
    ]

    users = await wearables_client.get_users()
    assert len(users) == 1
    assert users[0]["id"] == "user-retried"
    assert route.call_count == 2
