"""DataUpdateCoordinator for Requestarr."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_LIDARR_API_KEY,
    CONF_LIDARR_URL,
    CONF_RADARR_API_KEY,
    CONF_RADARR_URL,
    CONF_SONARR_API_KEY,
    CONF_SONARR_URL,
    CONF_TMDB_API_KEY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    TMDB_API_BASE,
)

_LOGGER = logging.getLogger(__name__)


class RequestarrCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data fetching from media services."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.config_entry = entry
        self._tmdb_api_key = entry.data.get(CONF_TMDB_API_KEY, "")
        self._radarr_url = entry.data.get(CONF_RADARR_URL, "")
        self._radarr_api_key = entry.data.get(CONF_RADARR_API_KEY, "")
        self._sonarr_url = entry.data.get(CONF_SONARR_URL, "")
        self._sonarr_api_key = entry.data.get(CONF_SONARR_API_KEY, "")
        self._lidarr_url = entry.data.get(CONF_LIDARR_URL, "")
        self._lidarr_api_key = entry.data.get(CONF_LIDARR_API_KEY, "")

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch library counts from arr services."""
        data: dict[str, Any] = {
            "radarr_movies": None,
            "sonarr_series": None,
            "lidarr_artists": None,
        }

        try:
            async with aiohttp.ClientSession() as session:
                if self._radarr_url and self._radarr_api_key:
                    data["radarr_movies"] = await self._fetch_arr_count(
                        session, self._radarr_url, self._radarr_api_key, "movie"
                    )
                if self._sonarr_url and self._sonarr_api_key:
                    data["sonarr_series"] = await self._fetch_arr_count(
                        session, self._sonarr_url, self._sonarr_api_key, "series"
                    )
                if self._lidarr_url and self._lidarr_api_key:
                    data["lidarr_artists"] = await self._fetch_arr_count(
                        session, self._lidarr_url, self._lidarr_api_key, "artist"
                    )
        except Exception as err:
            raise UpdateFailed(f"Error communicating with services: {err}") from err

        return data

    async def _fetch_arr_count(
        self, session: aiohttp.ClientSession, url: str, api_key: str, endpoint: str
    ) -> int | None:
        """Fetch item count from an arr service."""
        try:
            headers = {"X-Api-Key": api_key}
            async with session.get(
                f"{url}/api/v3/{endpoint}", headers=headers
            ) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return len(items) if isinstance(items, list) else None
        except Exception:
            _LOGGER.warning("Failed to fetch from %s", url)
        return None

    async def async_search_tmdb(
        self, query: str, media_type: str = "multi"
    ) -> list[dict[str, Any]]:
        """Search TMDB for movies, TV shows, or music."""
        try:
            async with aiohttp.ClientSession() as session:
                params = {"api_key": self._tmdb_api_key, "query": query}
                async with session.get(
                    f"{TMDB_API_BASE}/search/{media_type}", params=params
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("results", [])
        except Exception:
            _LOGGER.warning("TMDB search failed for query: %s", query)
        return []

    async def async_request_movie(self, tmdb_id: int) -> bool:
        """Send a movie to Radarr."""
        if not self._radarr_url or not self._radarr_api_key:
            return False
        # TODO: Implement Radarr add movie API call
        _LOGGER.info("Movie request queued: TMDB ID %s", tmdb_id)
        return True

    async def async_request_series(self, tmdb_id: int) -> bool:
        """Send a series to Sonarr."""
        if not self._sonarr_url or not self._sonarr_api_key:
            return False
        # TODO: Implement Sonarr add series API call
        _LOGGER.info("Series request queued: TMDB ID %s", tmdb_id)
        return True
