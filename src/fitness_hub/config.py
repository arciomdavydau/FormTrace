"""Configuration settings for fitness-mcp-hub using Pydantic Settings."""

from functools import lru_cache

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
    log_level: str = Field(default="INFO", description="Logging level")

    # Hevy API
    hevy_api_base_url: str = Field(
        default="https://api.hevyapp.com/v1",
        description="Base URL for Hevy API v1",
    )
    hevy_api_key: str = Field(
        default="",
        repr=False,
        description="API key for Hevy API",
    )
    fitness_timezone: str = Field(default="Europe/Warsaw", description="Report timezone")
    fitness_cache_seconds: int = Field(default=300, ge=0, description="In-memory cache TTL")

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
