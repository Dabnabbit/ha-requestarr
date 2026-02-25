"""DataUpdateCoordinator for Requestarr."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import ArrClient, CannotConnectError, InvalidAuthError
from .const import (
    CONF_LIDARR_API_KEY,
    CONF_LIDARR_URL,
    CONF_LIDARR_VERIFY_SSL,
    CONF_RADARR_API_KEY,
    CONF_RADARR_URL,
    CONF_RADARR_VERIFY_SSL,
    CONF_SONARR_API_KEY,
    CONF_SONARR_URL,
    CONF_SONARR_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_LIDARR,
    SERVICE_RADARR,
    SERVICE_SONARR,
)

_LOGGER = logging.getLogger(__name__)

# Map service types to their config key prefixes
_SERVICE_CONFIG = {
    SERVICE_RADARR: {
        "url": CONF_RADARR_URL,
        "api_key": CONF_RADARR_API_KEY,
        "verify_ssl": CONF_RADARR_VERIFY_SSL,
    },
    SERVICE_SONARR: {
        "url": CONF_SONARR_URL,
        "api_key": CONF_SONARR_API_KEY,
        "verify_ssl": CONF_SONARR_VERIFY_SSL,
    },
    SERVICE_LIDARR: {
        "url": CONF_LIDARR_URL,
        "api_key": CONF_LIDARR_API_KEY,
        "verify_ssl": CONF_LIDARR_VERIFY_SSL,
    },
}


class RequestarrCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage polling library counts from arr services.

    Polls all configured arr services every 5 minutes. Handles partial
    failure: if one service is down, others still update. Only raises
    UpdateFailed if ALL configured services fail.
    """

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
        session = async_get_clientsession(hass)

        # Build ArrClient instances for each configured service
        self._clients: dict[str, ArrClient] = {}
        for service_type, keys in _SERVICE_CONFIG.items():
            url = entry.data.get(keys["url"])
            if url:
                self._clients[service_type] = ArrClient(
                    base_url=url,
                    api_key=entry.data[keys["api_key"]],
                    service_type=service_type,
                    session=session,
                    verify_ssl=entry.data.get(keys["verify_ssl"], True),
                )

    @property
    def configured_services(self) -> list[str]:
        """Return list of configured service types."""
        return list(self._clients.keys())

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch library counts from all configured arr services.

        Returns a dict with:
        - {service_type}_count: int | None for each configured service
        - errors: dict of service_type -> error message for failed services

        Raises UpdateFailed only if ALL services fail.
        """
        data: dict[str, Any] = {}
        errors: dict[str, str] = {}

        for service_type, client in self._clients.items():
            try:
                count = await client.async_get_library_count()
                data[f"{service_type}_count"] = count
            except (CannotConnectError, InvalidAuthError) as err:
                _LOGGER.warning(
                    "Failed to poll %s: %s", service_type, err
                )
                errors[service_type] = str(err)
                data[f"{service_type}_count"] = None

        # If all configured services failed, raise UpdateFailed
        count_keys = [k for k in data if k.endswith("_count")]
        if count_keys and all(data[k] is None for k in count_keys):
            raise UpdateFailed(
                f"All arr services are unavailable: {errors}"
            )

        data["errors"] = errors
        return data
