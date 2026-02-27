"""Sensor platform for Requestarr."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import RequestarrConfigEntry
from .const import (
    CONF_LIDARR_URL,
    CONF_RADARR_URL,
    CONF_SONARR_URL,
    DOMAIN,
    SERVICE_LIDARR,
    SERVICE_RADARR,
    SERVICE_SONARR,
)
from .coordinator import RequestarrCoordinator

PARALLEL_UPDATES = 0

# Sensor configuration per service type
SERVICE_SENSOR_CONFIG: dict[str, dict[str, str]] = {
    SERVICE_RADARR: {
        "name": "Radarr",
        "icon": "mdi:movie",
        "url_key": CONF_RADARR_URL,
    },
    SERVICE_SONARR: {
        "name": "Sonarr",
        "icon": "mdi:television",
        "url_key": CONF_SONARR_URL,
    },
    SERVICE_LIDARR: {
        "name": "Lidarr",
        "icon": "mdi:music",
        "url_key": CONF_LIDARR_URL,
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RequestarrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for each configured arr service."""
    coordinator = entry.runtime_data.coordinator

    entities: list[RequestarrSensor] = []
    for service_type in coordinator.configured_services:
        entities.append(
            RequestarrSensor(coordinator, entry, service_type)
        )
    async_add_entities(entities)


class RequestarrSensor(CoordinatorEntity[RequestarrCoordinator], SensorEntity):
    """Sensor showing arr service status with library count as attribute.

    State: connected | disconnected | error
    Attributes: library_count, service_url, last_successful_sync
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RequestarrCoordinator,
        entry: ConfigEntry,
        service_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._service_type = service_type

        config = SERVICE_SENSOR_CONFIG[service_type]
        self._attr_unique_id = f"{entry.entry_id}_{service_type}"
        self._attr_name = config["name"]
        self._attr_icon = config["icon"]

        # Store the service URL for attributes (base URL only, no secrets)
        self._service_url = entry.data.get(config["url_key"], "")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            name="Requestarr",
            manufacturer="Requestarr",
        )

    @property
    def native_value(self) -> str | None:
        """Return the service status: connected, disconnected, or error."""
        if self.coordinator.data is None:
            return None

        errors = self.coordinator.data.get("errors", {})
        if self._service_type in errors:
            return "error"

        count = self.coordinator.data.get(f"{self._service_type}_count")
        if count is None:
            return "disconnected"

        return "connected"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional sensor attributes."""
        data = self.coordinator.data or {}
        return {
            "library_count": data.get(f"{self._service_type}_count"),
            "service_url": self._service_url,
            "last_successful_sync": data.get(
                f"{self._service_type}_last_sync"
            ),
        }
