"""API client for Requestarr."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class CannotConnectError(Exception):
    """Raised when a connection or timeout error occurs."""


class InvalidAuthError(Exception):
    """Raised when the API returns a 401 or 403 response."""


class ApiClient:
    """Generic API client with configurable auth, timeout, and error handling."""

    def __init__(
        self,
        host: str,
        port: int,
        api_key: str,
        session: aiohttp.ClientSession,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the API client."""
        self._base_url = f"http://{host}:{port}"
        self._api_key = api_key
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    def _get_auth_headers(self) -> dict[str, str]:
        """Return authorization headers.

        Override to use query param or body auth instead.
        """
        return {"Authorization": f"Bearer {self._api_key}"}

    async def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make an authenticated request to the API."""
        url = f"{self._base_url}{endpoint}"
        headers = self._get_auth_headers()
        try:
            response = await self._session.request(
                method,
                url,
                headers=headers,
                timeout=self._timeout,
                **kwargs,
            )
        except aiohttp.ClientConnectionError as err:
            raise CannotConnectError(f"Connection error: {err}") from err
        except aiohttp.ClientError as err:
            raise CannotConnectError(f"Client error: {err}") from err
        except asyncio.TimeoutError as err:
            raise CannotConnectError("Request timed out") from err

        if response.status in (401, 403):
            raise InvalidAuthError(
                f"Authentication failed (HTTP {response.status})"
            )

        response.raise_for_status()
        return await response.json()

    async def async_test_connection(self) -> bool:
        """Test the connection to the API.

        TODO: Replace /health with the actual health-check endpoint.
        """
        await self._request("GET", "/health")
        return True

    async def async_get_data(self) -> dict[str, Any]:
        """Fetch data from the API.

        TODO: Replace /api/data with the actual data endpoint.
        """
        return await self._request("GET", "/api/data")
