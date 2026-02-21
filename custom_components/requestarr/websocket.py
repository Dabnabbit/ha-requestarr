"""WebSocket API for the Requestarr integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

WS_TYPE_GET_DATA = f"{DOMAIN}/get_data"


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_GET_DATA,
    }
)
@websocket_api.async_response
async def websocket_get_data(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle get_data WebSocket command for Requestarr."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "No config entries")
        return

    coordinator = entries[0].runtime_data.coordinator
    connection.send_result(msg["id"], coordinator.data or {})


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register WebSocket commands for Requestarr."""
    websocket_api.async_register_command(hass, websocket_get_data)
