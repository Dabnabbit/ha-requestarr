"""The Requestarr integration - media requests for Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, FRONTEND_SCRIPT_URL
from .coordinator import RequestarrCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Requestarr from a config entry."""
    coordinator = RequestarrCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await _async_register_frontend(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register the frontend card resources."""
    frontend_path = Path(__file__).parent / "frontend"
    hass.http.register_static_path(
        FRONTEND_SCRIPT_URL,
        str(frontend_path / f"{DOMAIN}-card.js"),
        cache_headers=True,
    )
    _LOGGER.debug("Registered frontend card at %s", FRONTEND_SCRIPT_URL)
