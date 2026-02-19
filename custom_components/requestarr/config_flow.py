"""Config flow for Requestarr integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    CONF_LIDARR_API_KEY,
    CONF_LIDARR_URL,
    CONF_RADARR_API_KEY,
    CONF_RADARR_URL,
    CONF_SONARR_API_KEY,
    CONF_SONARR_URL,
    CONF_TMDB_API_KEY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_TMDB_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TMDB_API_KEY): str,
    }
)

STEP_RADARR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_RADARR_URL, default=""): str,
        vol.Optional(CONF_RADARR_API_KEY, default=""): str,
    }
)

STEP_SONARR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SONARR_URL, default=""): str,
        vol.Optional(CONF_SONARR_API_KEY, default=""): str,
    }
)

STEP_LIDARR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_LIDARR_URL, default=""): str,
        vol.Optional(CONF_LIDARR_API_KEY, default=""): str,
    }
)


class RequestarrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Requestarr."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: TMDB API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # TODO: Validate TMDB API key
            self._data.update(user_input)
            return await self.async_step_radarr()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_TMDB_SCHEMA,
            errors=errors,
        )

    async def async_step_radarr(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Radarr connection (optional)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # TODO: Validate Radarr connection if URL provided
            self._data.update(user_input)
            return await self.async_step_sonarr()

        return self.async_show_form(
            step_id="radarr",
            data_schema=STEP_RADARR_SCHEMA,
            errors=errors,
        )

    async def async_step_sonarr(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3: Sonarr connection (optional)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # TODO: Validate Sonarr connection if URL provided
            self._data.update(user_input)
            return await self.async_step_lidarr()

        return self.async_show_form(
            step_id="sonarr",
            data_schema=STEP_SONARR_SCHEMA,
            errors=errors,
        )

    async def async_step_lidarr(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 4: Lidarr connection (optional)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # TODO: Validate Lidarr connection if URL provided
            self._data.update(user_input)
            return self.async_create_entry(
                title="Requestarr",
                data=self._data,
            )

        return self.async_show_form(
            step_id="lidarr",
            data_schema=STEP_LIDARR_SCHEMA,
            errors=errors,
        )
