"""Synthetic Hevy fixtures and isolated HTTP mocks shared by tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from fitness_hub.config import Settings

_FIXTURES = Path(__file__).parent / "fixtures" / "hevy"


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        _env_file=None,
        mcp_server_name="test-fitness-mcp-hub",
        hevy_api_base_url="https://api.hevyapp.com/v1",
        hevy_api_key="mock-hevy-api-key",
        request_timeout=5.0,
        max_retries=2,
    )


@pytest.fixture
def sample_hevy_workouts_payload() -> dict[str, Any]:
    return json.loads((_FIXTURES / "workouts_page.json").read_text())


@pytest.fixture
def sample_hevy_exercise_templates_payload() -> dict[str, Any]:
    return json.loads((_FIXTURES / "exercise_templates_page.json").read_text())


@pytest.fixture
def mocked_hevy_api(
    respx_mock: respx.MockRouter,
    sample_hevy_workouts_payload: dict[str, Any],
    sample_hevy_exercise_templates_payload: dict[str, Any],
) -> respx.MockRouter:
    respx_mock.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json=sample_hevy_workouts_payload)
    )
    respx_mock.get("https://api.hevyapp.com/v1/exercise_templates").mock(
        return_value=httpx.Response(200, json=sample_hevy_exercise_templates_payload)
    )
    return respx_mock
