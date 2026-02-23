"""The Requestarr integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, FRONTEND_SCRIPT_URL
from .coordinator import TemplateCoordinator

from .websocket import async_setup_websocket


from .services import async_register_services



_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class RequestarrData:
    """Data for the Requestarr integration."""

    coordinator: TemplateCoordinator



type RequestarrConfigEntry = ConfigEntry[
    RequestarrData
]


async def _async_register_lovelace_resource(lovelace) -> None:
    """Register the card JS as a Lovelace resource if not already present."""
    url = FRONTEND_SCRIPT_URL
    existing = [
        r for r in lovelace.resources.async_items() if url in r.get("url", "")
    ]
    if not existing:
        await lovelace.resources.async_create_item(
            {"res_type": "module", "url": url}
        )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Requestarr integration."""
    frontend_path = Path(__file__).parent / "frontend"
    try:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    FRONTEND_SCRIPT_URL,
                    str(frontend_path / f"{DOMAIN}-card.js"),
                    cache_headers=True,
                )
            ]
        )
    except RuntimeError:
        # Path already registered — happens on reload
        pass

    # Auto-register as Lovelace resource (storage mode only)
    try:
        lovelace = hass.data.get("lovelace")
        if lovelace and getattr(lovelace, "mode", None) == "storage":
            if lovelace.resources.loaded:
                await _async_register_lovelace_resource(lovelace)
            else:
                async def _on_lovelace_loaded(_event=None):
                    await _async_register_lovelace_resource(lovelace)
                hass.bus.async_listen_once("lovelace_updated", _on_lovelace_loaded)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not auto-register Lovelace resource; add manually")


    async_setup_websocket(hass)


    async_register_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: RequestarrConfigEntry) -> bool:
    """Set up Requestarr from a config entry."""
    coordinator = TemplateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()



    entry.runtime_data = RequestarrData(coordinator=coordinator)


    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RequestarrConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
