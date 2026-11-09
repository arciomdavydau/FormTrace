"""Upstream API clients for Wearables, Hevy, and Nutrition."""

from fitness_hub.clients.base import (
    AuthenticationError,
    BaseAsyncClient,
    NotFoundError,
    RateLimitError,
    UpstreamAPIError,
)
from fitness_hub.clients.hevy import HevyClient
from fitness_hub.clients.nutrition import NutritionAdapter
from fitness_hub.clients.wearables import WearablesClient

__all__ = [
    "AuthenticationError",
    "BaseAsyncClient",
    "HevyClient",
    "NotFoundError",
    "NutritionAdapter",
    "RateLimitError",
    "UpstreamAPIError",
    "WearablesClient",
]
