"""Configuration settings for Fitness MCP Server using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
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
    mcp_server_name: str = Field(default="fitness-mcp-server", description="MCP server name")
    mcp_transport: Literal["stdio", "sse"] = Field(
        default="stdio",
        description="Transport protocol for MCP server (stdio or sse)",
    )
    mcp_host: str = Field(default="0.0.0.0", description="Host to bind for SSE transport")
    mcp_port: int = Field(default=8000, description="Port to bind for SSE transport")
    log_level: str = Field(default="INFO", description="Logging level")

    # Open Wearables API
    open_wearables_api_url: str = Field(
        default="https://example.invalid",
        description="Base URL for Open Wearables REST API",
    )
    open_wearables_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="API key for Open Wearables authentication",
    )
    open_wearables_default_user_id: str | None = Field(
        default=None,
        description="Default user ID to query if none is provided",
    )
    open_wearables_timeout: float = Field(
        default=30.0,
        description="HTTP request timeout for Open Wearables API in seconds",
    )

    # Hevy API
    hevy_api_url: str = Field(
        default="https://api.hevyapp.com/v1",
        description="Base URL for Hevy REST API",
    )
    hevy_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="API key for Hevy (requires Hevy Pro)",
    )
    hevy_timeout: float = Field(
        default=30.0,
        description="HTTP request timeout for Hevy API in seconds",
    )

    # Nutrition Service
    nutrition_provider: Literal["manual", "myfitnesspal"] = Field(
        default="manual",
        description="Nutrition data provider (manual storage or myfitnesspal)",
    )
    nutrition_data_path: str = Field(
        default="./data/nutrition_logs.json",
        description="File path for persisting manual nutrition logs",
    )
    myfitnesspal_username: str | None = Field(
        default=None,
        description="MyFitnessPal username (if using MFP adapter)",
    )
    myfitnesspal_password: SecretStr | None = Field(
        default=None,
        description="MyFitnessPal password (if using MFP adapter)",
    )

    # General HTTP Client & Retry Settings
    request_timeout: float = Field(
        default=30.0,
        description="Default HTTP request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for transient HTTP failures",
    )
    backoff_factor: float = Field(
        default=0.5,
        description="Multiplier for exponential backoff between retries",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached instance of Settings."""
    return Settings()


settings = get_settings()
