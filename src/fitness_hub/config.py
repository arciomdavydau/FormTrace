"""Configuration settings for fitness-mcp-hub using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # MCP Server
    mcp_server_name: str = Field(default="fitness-mcp-hub", description="MCP server name")
    mcp_transport: Literal["stdio", "sse"] = Field(
        default="stdio",
        description="Transport protocol for FastMCP",
    )
    mcp_host: str = Field(default="0.0.0.0", description="Host to bind for SSE transport")
    mcp_port: int = Field(default=8000, description="Port to bind for SSE transport")
    log_level: str = Field(default="INFO", description="Logging level")

    # Open Wearables API
    open_wearables_base_url: str = Field(
        default="http://localhost:8080",
        description="Base URL for Open Wearables service",
    )
    open_wearables_api_key: str = Field(
        default="",
        description="API key for Open Wearables service",
    )

    # Hevy API
    hevy_api_base_url: str = Field(
        default="https://api.hevyapp.com/v1",
        description="Base URL for Hevy API v1",
    )
    hevy_api_key: str = Field(
        default="",
        description="API key for Hevy API",
    )

    # Nutrition Adapter
    nutrition_provider: str = Field(
        default="local",
        description="Nutrition data provider (local or myfitnesspal)",
    )
    nutrition_data_path: str = Field(
        default="./data/nutrition_logs.json",
        description="Path to local JSON persistence file for nutrition records",
    )

    # Targets & Baselines
    target_daily_calories: int = Field(
        default=2200,
        description="Target daily calorie intake in kcal",
    )
    target_protein_g: int = Field(
        default=180,
        description="Target daily protein intake in grams",
    )
    target_daily_steps: int = Field(
        default=9000,
        description="Target daily step count",
    )

    # HTTP Client Defaults
    request_timeout: float = Field(
        default=30.0,
        description="Default HTTP timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts on transient network errors",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton instance of Settings."""
    return Settings()


settings = get_settings()
