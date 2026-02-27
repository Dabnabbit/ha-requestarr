"""API client for Requestarr — uniform client for Radarr, Sonarr, and Lidarr."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_VERSIONS, DEFAULT_TIMEOUT, LIBRARY_ENDPOINTS, LOOKUP_ENDPOINTS

_LOGGER = logging.getLogger(__name__)


class CannotConnectError(Exception):
    """Raised when a connection or timeout error occurs."""


class InvalidAuthError(Exception):
    """Raised when the API returns a 401 or 403 response."""


class ServerError(Exception):
    """Raised when the server returns a non-auth HTTP error (4xx/5xx)."""


class ArrClient:
    """Uniform API client for Radarr, Sonarr, and Lidarr.

    Handles API version differences automatically:
    - Radarr: /api/v3/
    - Sonarr: /api/v3/
    - Lidarr: /api/v1/

    All services use X-Api-Key header authentication.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        service_type: str,
        session: aiohttp.ClientSession,
        verify_ssl: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the arr API client.

        Args:
            base_url: User-entered base URL (e.g., http://192.168.1.50:7878).
            api_key: API key for the arr service.
            service_type: One of 'radarr', 'sonarr', 'lidarr'.
            session: Shared aiohttp session from HA.
            verify_ssl: Whether to verify SSL certificates.
            timeout: Request timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._service_type = service_type
        self._api_version = API_VERSIONS[service_type]
        self._session = session
        self._ssl: bool | None = None if verify_ssl else False
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def _api_base(self) -> str:
        """Return the API base URL including version prefix."""
        return f"{self._base_url}/api/{self._api_version}"

    def _headers(self) -> dict[str, str]:
        """Return authentication headers."""
        return {"X-Api-Key": self._api_key}

    async def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Any:
        """Make an authenticated request to the arr API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path (e.g., /system/status).
            **kwargs: Additional arguments passed to aiohttp.

        Returns:
            Parsed JSON response, or empty dict if response body is empty.

        Raises:
            CannotConnectError: On connection/timeout errors.
            InvalidAuthError: On 401/403 responses.
            ServerError: On other 4xx/5xx responses.
        """
        url = f"{self._api_base}{endpoint}"
        try:
            response = await self._session.request(
                method,
                url,
                headers=self._headers(),
                ssl=self._ssl,
                timeout=self._timeout,
                **kwargs,
            )
        except aiohttp.ClientConnectionError as err:
            raise CannotConnectError(
                f"Connection error to {self._service_type}: {err}"
            ) from err
        except aiohttp.ClientError as err:
            raise CannotConnectError(
                f"Client error for {self._service_type}: {err}"
            ) from err
        except asyncio.TimeoutError as err:
            raise CannotConnectError(
                f"Request to {self._service_type} timed out"
            ) from err

        if response.status in (401, 403):
            raise InvalidAuthError(
                f"Authentication failed for {self._service_type} "
                f"(HTTP {response.status})"
            )

        if response.status >= 400:
            raise ServerError(
                f"{self._service_type} returned HTTP {response.status}: "
                f"{response.reason}"
            )

        # Handle empty response bodies (some endpoints return 200 with no body)
        text = await response.text()
        if not text or not text.strip():
            return {}

        return await response.json(content_type=None)

    async def async_validate_connection(self) -> bool:
        """Validate the connection via /system/status.

        Returns:
            True if connection is valid.

        Raises:
            CannotConnectError: Cannot reach the service.
            InvalidAuthError: API key is invalid.
        """
        await self._request("GET", "/system/status")
        return True

    async def async_get_quality_profiles(self) -> list[dict[str, Any]]:
        """Fetch quality profiles from the arr service.

        Returns:
            List of quality profile dicts with at least 'id' and 'name'.
        """
        return await self._request("GET", "/qualityprofile")

    async def async_get_root_folders(self) -> list[dict[str, Any]]:
        """Fetch root folders from the arr service.

        Returns:
            List of root folder dicts with at least 'id' and 'path'.
        """
        return await self._request("GET", "/rootfolder")

    async def async_get_metadata_profiles(self) -> list[dict[str, Any]]:
        """Fetch metadata profiles from Lidarr.

        Only applicable to Lidarr. Radarr and Sonarr do not have
        metadata profiles.

        Returns:
            List of metadata profile dicts with at least 'id' and 'name'.
        """
        return await self._request("GET", "/metadataprofile")

    async def async_search(self, query: str) -> list[dict[str, Any]]:
        """Search the arr service's lookup endpoint.

        Args:
            query: Search term.

        Returns:
            List of raw result dicts from the arr API.
        """
        endpoint = LOOKUP_ENDPOINTS[self._service_type]
        return await self._request("GET", endpoint, params={"term": query})

    async def async_get_library_count(self) -> int:
        """Fetch the total number of items in the library.

        Uses the service-specific library endpoint:
        - Radarr: /movie (returns all movies)
        - Sonarr: /series (returns all series)
        - Lidarr: /artist (returns all artists)

        Returns:
            Total count of library items.
        """
        endpoint = LIBRARY_ENDPOINTS[self._service_type]
        items = await self._request("GET", endpoint)
        if isinstance(items, list):
            return len(items)
        return 0
