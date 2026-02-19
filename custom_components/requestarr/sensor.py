"""Sensor platform for Requestarr."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RequestarrCoordinator

SENSOR_TYPES = {
    "radarr_movies": {"name": "Radarr Movies", "icon": "mdi:movie-outline"},
    "sonarr_series": {"name": "Sonarr Series", "icon": "mdi:television-classic"},
    "lidarr_artists": {"name": "Lidarr Artists", "icon": "mdi:music"},
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: RequestarrCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        RequestarrSensor(coordinator, entry, sensor_type, info)
        for sensor_type, info in SENSOR_TYPES.items()
    ]
    async_add_entities(entities)


class RequestarrSensor(CoordinatorEntity[RequestarrCoordinator], SensorEntity):
    """Representation of a Requestarr sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: RequestarrCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        info: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_name = info["name"]
        self._attr_icon = info["icon"]

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._sensor_type)
