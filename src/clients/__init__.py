"""HTTP API clients for Wearables, Hevy, and Nutrition services."""

from src.clients.base import (
    APIError,
    AuthenticationError,
    BaseAsyncHTTPClient,
    ConfigurationError,
    FitnessMCPError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
)
from src.clients.hevy import HevyClient
from src.clients.nutrition import NutritionClient
from src.clients.wearables import OpenWearablesClient

__all__ = [
    "APIError",
    "AuthenticationError",
    "BaseAsyncHTTPClient",
    "ConfigurationError",
    "FitnessMCPError",
    "HevyClient",
    "NotFoundError",
    "NutritionClient",
    "OpenWearablesClient",
    "RateLimitError",
    "ServiceUnavailableError",
]
