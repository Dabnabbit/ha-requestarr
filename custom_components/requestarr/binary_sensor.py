"""Binary sensor platform for Requestarr."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import RequestarrConfigEntry
from .const import DOMAIN
from .coordinator import TemplateCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RequestarrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([TemplateStatusSensor(coordinator, entry)])


class TemplateStatusSensor(CoordinatorEntity[TemplateCoordinator], BinarySensorEntity):
    """Binary sensor indicating service connectivity."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: TemplateCoordinator,
        entry: RequestarrConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_name = "Status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            name=entry.title,
            manufacturer="Requestarr",
        )

    @property
    def is_on(self) -> bool:
        """Return True if the service is reachable."""
        return self.coordinator.last_update_success
