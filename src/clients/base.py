"""Base asynchronous HTTP client with robust retry mechanisms, rate limit handling, and custom error types."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class FitnessMCPError(Exception):
    """Base exception for all Fitness MCP Server errors."""


class ConfigurationError(FitnessMCPError):
    """Raised when required configuration or API credentials are missing."""


class APIError(FitnessMCPError):
    """Base exception for HTTP API errors."""

    def __init__(self, message: str, status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class AuthenticationError(APIError):
    """Raised when authentication with an external service fails (401/403)."""


class NotFoundError(APIError):
    """Raised when a requested resource is not found (404)."""


class RateLimitError(APIError):
    """Raised when rate limits are exceeded (429)."""

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        retry_after: float | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message, status_code=status_code, details=details)
        self.retry_after = retry_after


class ServiceUnavailableError(APIError):
    """Raised when the upstream service is temporarily unavailable (502/503/504)."""


class BaseAsyncHTTPClient:
    """Base asynchronous HTTP client equipped with retries, backoff, and error mapping."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or initialize the underlying httpx AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> BaseAsyncHTTPClient:
        await self.get_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.close()

    def _sanitize_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        """Sanitize sensitive authorization headers for safe logging."""
        if not headers:
            return {}
        sanitized = {}
        sensitive_keys = {"authorization", "api-key", "x-api-key", "x-open-wearables-api-key"}
        for k, v in headers.items():
            if k.lower() in sensitive_keys:
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = v
        return sanitized

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """
        Execute an HTTP request with exponential backoff on transient errors and rate limits.
        """
        client = await self.get_client()
        url = (
            endpoint
            if endpoint.startswith(("http://", "https://"))
            else f"{self.base_url}{endpoint}"
        )

        clean_params = None
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}

        attempt = 0
        while True:
            attempt += 1
            try:
                logger.debug(
                    "HTTP %s request to %s (attempt %d/%d)",
                    method,
                    url,
                    attempt,
                    self.max_retries,
                )
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=clean_params,
                    json=json,
                    **kwargs,
                )

                if response.status_code == 401 or response.status_code == 403:
                    raise AuthenticationError(
                        f"Authentication failed ({response.status_code}): {response.text}",
                        status_code=response.status_code,
                    )

                if response.status_code == 404:
                    raise NotFoundError(
                        f"Resource not found at {endpoint}: {response.text}",
                        status_code=404,
                    )

                if response.status_code == 429:
                    retry_after_header = response.headers.get("Retry-After")
                    retry_after_val: float | None = None
                    if retry_after_header:
                        try:
                            retry_after_val = float(retry_after_header)
                        except ValueError:
                            retry_after_val = None

                    if attempt < self.max_retries:
                        sleep_time = (
                            retry_after_val
                            if retry_after_val is not None
                            else self.backoff_factor * (2 ** (attempt - 1))
                        )
                        logger.warning(
                            "Rate limit (429) hit for %s. Backing off for %.2f seconds.",
                            url,
                            sleep_time,
                        )
                        await asyncio.sleep(sleep_time)
                        continue

                    raise RateLimitError(
                        f"Rate limit exceeded on {endpoint}: {response.text}",
                        retry_after=retry_after_val,
                    )

                if response.status_code in {502, 503, 504}:
                    if attempt < self.max_retries:
                        sleep_time = self.backoff_factor * (2 ** (attempt - 1))
                        logger.warning(
                            "Upstream error %d on %s. Retrying in %.2f seconds.",
                            response.status_code,
                            url,
                            sleep_time,
                        )
                        await asyncio.sleep(sleep_time)
                        continue

                    raise ServiceUnavailableError(
                        f"Upstream service unavailable ({response.status_code}) on {endpoint}: {response.text}",
                        status_code=response.status_code,
                    )

                response.raise_for_status()

                # If no content, return empty dict
                if response.status_code == 204 or not response.content:
                    return {}

                return response.json()  # type: ignore[no-any-return]

            except (httpx.TimeoutException, httpx.NetworkError) as err:
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        "Network/Timeout error (%s) contacting %s. Retrying in %.2f seconds.",
                        type(err).__name__,
                        url,
                        sleep_time,
                    )
                    await asyncio.sleep(sleep_time)
                    continue
                raise APIError(
                    f"Network error after {self.max_retries} attempts for {url}: {err}"
                ) from err
