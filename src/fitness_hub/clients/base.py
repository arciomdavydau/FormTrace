"""Base asynchronous HTTP client with timeout, headers, retry backoff, and custom error types."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class UpstreamAPIError(Exception):
    """Base exception for errors communicating with upstream health/fitness APIs."""

    def __init__(self, message: str, status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class AuthenticationError(UpstreamAPIError):
    """Raised when authentication with an upstream API fails (401/403)."""


class NotFoundError(UpstreamAPIError):
    """Raised when an upstream resource is not found (404)."""


class RateLimitError(UpstreamAPIError):
    """Raised when an upstream rate limit is encountered (429)."""

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        retry_after: float | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message, status_code=status_code, details=details)
        self.retry_after = retry_after


class BaseAsyncClient:
    """Async context manager wrapper around httpx.AsyncClient with retries and error handling."""

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
        """Initialize or return the cached httpx AsyncClient instance."""
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

    async def __aenter__(self) -> BaseAsyncClient:
        await self.get_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.close()

    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """
        Execute an asynchronous HTTP request with exponential backoff on transient errors.
        """
        client = await self.get_client()
        clean_path = path if path.startswith("/") else f"/{path}"
        url = (
            clean_path
            if path.startswith(("http://", "https://"))
            else f"{self.base_url}{clean_path}"
        )

        clean_params = None
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}

        attempt = 0
        while True:
            attempt += 1
            try:
                logger.debug(
                    "HTTP %s %s (attempt %d/%d)",
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

                if response.status_code in {401, 403}:
                    raise AuthenticationError(
                        f"Authentication failed ({response.status_code}) on {url}",
                        status_code=response.status_code,
                    )

                if response.status_code == 404:
                    raise NotFoundError(
                        f"Resource not found at {url}",
                        status_code=404,
                    )

                if response.status_code == 429:
                    retry_header = response.headers.get("Retry-After")
                    retry_after = (
                        float(retry_header) if retry_header and retry_header.isdigit() else None
                    )
                    if attempt < self.max_retries:
                        delay = retry_after or (self.backoff_factor * (2 ** (attempt - 1)))
                        logger.warning("Rate limit hit on %s. Retrying in %.2fs", url, delay)
                        await asyncio.sleep(delay)
                        continue
                    raise RateLimitError(
                        f"Rate limit exceeded on {url}",
                        retry_after=retry_after,
                    )

                if response.status_code in {502, 503, 504}:
                    if attempt < self.max_retries:
                        delay = self.backoff_factor * (2 ** (attempt - 1))
                        logger.warning(
                            "Server error %d on %s. Retrying in %.2fs",
                            response.status_code,
                            url,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise UpstreamAPIError(
                        f"Upstream service unavailable ({response.status_code}) on {url}",
                        status_code=response.status_code,
                    )

                response.raise_for_status()

                if response.status_code == 204 or not response.content:
                    return {}

                return response.json()  # type: ignore[no-any-return]

            except (httpx.TimeoutException, httpx.NetworkError) as err:
                if attempt < self.max_retries:
                    delay = self.backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        "Network/Timeout error (%s) contacting %s. Retrying in %.2fs",
                        type(err).__name__,
                        url,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise UpstreamAPIError(
                    f"Network error after {self.max_retries} attempts for {url}: {err}"
                ) from err
