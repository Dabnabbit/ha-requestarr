"""Service handlers for the Requestarr integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_QUERY = "query"

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("query"): cv.string,
    }
)


async def _async_handle_query(call: ServiceCall) -> ServiceResponse:
    """Handle the query service call for Requestarr."""
    # TODO: Implement with actual coordinator/client data
    result: dict[str, Any] = {"query": call.data["query"], "results": []}
    if call.return_response:
        return result
    return None


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register integration service actions for Requestarr."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_QUERY,
        _async_handle_query,
        schema=SERVICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
