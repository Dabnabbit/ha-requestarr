"""Config flow for Requestarr integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .api import ArrClient, CannotConnectError, InvalidAuthError
from .const import (
    CONF_LIDARR_API_KEY,
    CONF_LIDARR_FOLDERS,
    CONF_LIDARR_METADATA_PROFILE_ID,
    CONF_LIDARR_METADATA_PROFILES,
    CONF_LIDARR_PROFILES,
    CONF_LIDARR_QUALITY_PROFILE_ID,
    CONF_LIDARR_ROOT_FOLDER,
    CONF_LIDARR_URL,
    CONF_LIDARR_VERIFY_SSL,
    CONF_RADARR_API_KEY,
    CONF_RADARR_FOLDERS,
    CONF_RADARR_PROFILES,
    CONF_RADARR_QUALITY_PROFILE_ID,
    CONF_RADARR_ROOT_FOLDER,
    CONF_RADARR_URL,
    CONF_RADARR_VERIFY_SSL,
    CONF_SONARR_API_KEY,
    CONF_SONARR_FOLDERS,
    CONF_SONARR_PROFILES,
    CONF_SONARR_QUALITY_PROFILE_ID,
    CONF_SONARR_ROOT_FOLDER,
    CONF_SONARR_URL,
    CONF_SONARR_VERIFY_SSL,
    DOMAIN,
    SERVICE_LIDARR,
    SERVICE_RADARR,
    SERVICE_SONARR,
)

_LOGGER = logging.getLogger(__name__)

# Skip field keys (not stored in config entry)
SKIP_RADARR = "skip_radarr"
SKIP_SONARR = "skip_sonarr"
SKIP_LIDARR = "skip_lidarr"

# Refresh profiles field key (options flow)
REFRESH_PROFILES = "refresh_profiles"


def _build_step_schema(
    url_key: str,
    api_key_key: str,
    verify_ssl_key: str,
    skip_key: str,
) -> vol.Schema:
    """Build a config flow step schema for an arr service."""
    return vol.Schema(
        {
            vol.Optional(url_key, default=""): str,
            vol.Optional(api_key_key, default=""): str,
            vol.Optional(verify_ssl_key, default=True): bool,
            vol.Optional(skip_key, default=False): bool,
        }
    )


STEP_RADARR_SCHEMA = _build_step_schema(
    CONF_RADARR_URL, CONF_RADARR_API_KEY, CONF_RADARR_VERIFY_SSL, SKIP_RADARR
)
STEP_SONARR_SCHEMA = _build_step_schema(
    CONF_SONARR_URL, CONF_SONARR_API_KEY, CONF_SONARR_VERIFY_SSL, SKIP_SONARR
)
STEP_LIDARR_SCHEMA = _build_step_schema(
    CONF_LIDARR_URL, CONF_LIDARR_API_KEY, CONF_LIDARR_VERIFY_SSL, SKIP_LIDARR
)


async def _validate_and_fetch(
    hass: HomeAssistant,
    service_type: str,
    url: str,
    api_key: str,
    verify_ssl: bool,
) -> dict[str, Any]:
    """Validate connection and fetch profiles/folders from an arr service.

    Returns:
        Dict with profiles, folders, default profile ID, default folder path,
        and (for Lidarr) metadata profiles and default metadata profile ID.

    Raises:
        CannotConnectError: Cannot reach the service.
        InvalidAuthError: API key is invalid.
    """
    session = async_get_clientsession(hass)
    client = ArrClient(
        base_url=url,
        api_key=api_key,
        service_type=service_type,
        session=session,
        verify_ssl=verify_ssl,
    )

    # Validate connection first
    await client.async_validate_connection()

    # Fetch profiles and folders
    profiles = await client.async_get_quality_profiles()
    folders = await client.async_get_root_folders()

    result: dict[str, Any] = {
        "profiles": [{"id": p["id"], "name": p["name"]} for p in profiles],
        "folders": [{"id": f["id"], "path": f["path"]} for f in folders],
        "quality_profile_id": profiles[0]["id"] if profiles else None,
        "root_folder": folders[0]["path"] if folders else None,
    }

    # Lidarr also needs metadata profiles
    if service_type == SERVICE_LIDARR:
        metadata_profiles = await client.async_get_metadata_profiles()
        result["metadata_profiles"] = [
            {"id": p["id"], "name": p["name"]} for p in metadata_profiles
        ]
        result["metadata_profile_id"] = (
            metadata_profiles[0]["id"] if metadata_profiles else None
        )

    return result


def _has_any_service(data: dict[str, Any]) -> bool:
    """Check if at least one arr service is configured."""
    return bool(
        data.get(CONF_RADARR_URL)
        or data.get(CONF_SONARR_URL)
        or data.get(CONF_LIDARR_URL)
    )


class RequestarrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Requestarr."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> RequestarrOptionsFlowHandler:
        """Create the options flow."""
        return RequestarrOptionsFlowHandler()

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step — redirect to Radarr."""
        return await self.async_step_radarr()

    async def async_step_radarr(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle Radarr configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get(SKIP_RADARR):
                return await self.async_step_sonarr()

            url = user_input.get(CONF_RADARR_URL, "").strip().rstrip("/")
            api_key = user_input.get(CONF_RADARR_API_KEY, "").strip()

            if not url:
                errors[CONF_RADARR_URL] = "cannot_connect"
            elif not api_key:
                errors[CONF_RADARR_API_KEY] = "invalid_auth"
            else:
                try:
                    fetched = await _validate_and_fetch(
                        self.hass,
                        SERVICE_RADARR,
                        url,
                        api_key,
                        user_input.get(CONF_RADARR_VERIFY_SSL, True),
                    )
                except InvalidAuthError:
                    errors[CONF_RADARR_API_KEY] = "invalid_auth"
                except CannotConnectError:
                    errors[CONF_RADARR_URL] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error validating Radarr")
                    errors["base"] = "cannot_fetch_profiles"
                else:
                    self._data[CONF_RADARR_URL] = url
                    self._data[CONF_RADARR_API_KEY] = api_key
                    self._data[CONF_RADARR_VERIFY_SSL] = user_input.get(
                        CONF_RADARR_VERIFY_SSL, True
                    )
                    self._data[CONF_RADARR_PROFILES] = fetched["profiles"]
                    self._data[CONF_RADARR_FOLDERS] = fetched["folders"]
                    self._data[CONF_RADARR_QUALITY_PROFILE_ID] = fetched[
                        "quality_profile_id"
                    ]
                    self._data[CONF_RADARR_ROOT_FOLDER] = fetched[
                        "root_folder"
                    ]
                    return await self.async_step_sonarr()

        return self.async_show_form(
            step_id="radarr",
            data_schema=STEP_RADARR_SCHEMA,
            errors=errors,
            description_placeholders={
                "url_example": "http://192.168.1.50:7878"
            },
        )

    async def async_step_sonarr(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle Sonarr configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get(SKIP_SONARR):
                return await self.async_step_lidarr()

            url = user_input.get(CONF_SONARR_URL, "").strip().rstrip("/")
            api_key = user_input.get(CONF_SONARR_API_KEY, "").strip()

            if not url:
                errors[CONF_SONARR_URL] = "cannot_connect"
            elif not api_key:
                errors[CONF_SONARR_API_KEY] = "invalid_auth"
            else:
                try:
                    fetched = await _validate_and_fetch(
                        self.hass,
                        SERVICE_SONARR,
                        url,
                        api_key,
                        user_input.get(CONF_SONARR_VERIFY_SSL, True),
                    )
                except InvalidAuthError:
                    errors[CONF_SONARR_API_KEY] = "invalid_auth"
                except CannotConnectError:
                    errors[CONF_SONARR_URL] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error validating Sonarr")
                    errors["base"] = "cannot_fetch_profiles"
                else:
                    self._data[CONF_SONARR_URL] = url
                    self._data[CONF_SONARR_API_KEY] = api_key
                    self._data[CONF_SONARR_VERIFY_SSL] = user_input.get(
                        CONF_SONARR_VERIFY_SSL, True
                    )
                    self._data[CONF_SONARR_PROFILES] = fetched["profiles"]
                    self._data[CONF_SONARR_FOLDERS] = fetched["folders"]
                    self._data[CONF_SONARR_QUALITY_PROFILE_ID] = fetched[
                        "quality_profile_id"
                    ]
                    self._data[CONF_SONARR_ROOT_FOLDER] = fetched[
                        "root_folder"
                    ]
                    return await self.async_step_lidarr()

        return self.async_show_form(
            step_id="sonarr",
            data_schema=STEP_SONARR_SCHEMA,
            errors=errors,
            description_placeholders={
                "url_example": "http://192.168.1.50:8989"
            },
        )

    async def async_step_lidarr(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle Lidarr configuration step (final step)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get(SKIP_LIDARR):
                # Check if at least one service is configured
                if not _has_any_service(self._data):
                    errors["base"] = "no_services"
                else:
                    return await self._create_entry()
            else:
                url = user_input.get(CONF_LIDARR_URL, "").strip().rstrip("/")
                api_key = user_input.get(CONF_LIDARR_API_KEY, "").strip()

                if not url:
                    errors[CONF_LIDARR_URL] = "cannot_connect"
                elif not api_key:
                    errors[CONF_LIDARR_API_KEY] = "invalid_auth"
                else:
                    try:
                        fetched = await _validate_and_fetch(
                            self.hass,
                            SERVICE_LIDARR,
                            url,
                            api_key,
                            user_input.get(CONF_LIDARR_VERIFY_SSL, True),
                        )
                    except InvalidAuthError:
                        errors[CONF_LIDARR_API_KEY] = "invalid_auth"
                    except CannotConnectError:
                        errors[CONF_LIDARR_URL] = "cannot_connect"
                    except Exception:
                        _LOGGER.exception(
                            "Unexpected error validating Lidarr"
                        )
                        errors["base"] = "cannot_fetch_profiles"
                    else:
                        self._data[CONF_LIDARR_URL] = url
                        self._data[CONF_LIDARR_API_KEY] = api_key
                        self._data[CONF_LIDARR_VERIFY_SSL] = user_input.get(
                            CONF_LIDARR_VERIFY_SSL, True
                        )
                        self._data[CONF_LIDARR_PROFILES] = fetched["profiles"]
                        self._data[CONF_LIDARR_FOLDERS] = fetched["folders"]
                        self._data[CONF_LIDARR_QUALITY_PROFILE_ID] = fetched[
                            "quality_profile_id"
                        ]
                        self._data[CONF_LIDARR_ROOT_FOLDER] = fetched[
                            "root_folder"
                        ]
                        self._data[CONF_LIDARR_METADATA_PROFILES] = fetched[
                            "metadata_profiles"
                        ]
                        self._data[CONF_LIDARR_METADATA_PROFILE_ID] = fetched[
                            "metadata_profile_id"
                        ]
                        return await self._create_entry()

        return self.async_show_form(
            step_id="lidarr",
            data_schema=STEP_LIDARR_SCHEMA,
            errors=errors,
            description_placeholders={
                "url_example": "http://192.168.1.50:8686"
            },
        )

    async def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry after all steps are complete."""
        # Singleton integration — only one instance allowed
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="Requestarr",
            data=self._data,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration — re-run wizard with current values."""
        # Pre-fill self._data with current config entry values
        self._data = dict(self.config_entry.data)
        return await self.async_step_radarr()


class RequestarrOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Requestarr."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        data = dict(self.config_entry.data)

        if user_input is not None:
            # Handle profile refresh
            if user_input.get(REFRESH_PROFILES):
                try:
                    data = await self._refresh_profiles(data)
                except (CannotConnectError, InvalidAuthError) as err:
                    _LOGGER.warning("Failed to refresh profiles: %s", err)
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error refreshing profiles")
                    errors["base"] = "unknown"

            if not errors:
                # Update selected profiles and folders
                for key in (
                    CONF_RADARR_QUALITY_PROFILE_ID,
                    CONF_RADARR_ROOT_FOLDER,
                    CONF_RADARR_VERIFY_SSL,
                    CONF_SONARR_QUALITY_PROFILE_ID,
                    CONF_SONARR_ROOT_FOLDER,
                    CONF_SONARR_VERIFY_SSL,
                    CONF_LIDARR_QUALITY_PROFILE_ID,
                    CONF_LIDARR_ROOT_FOLDER,
                    CONF_LIDARR_METADATA_PROFILE_ID,
                    CONF_LIDARR_VERIFY_SSL,
                ):
                    if key in user_input:
                        data[key] = user_input[key]

                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=data
                )
                await self.hass.config_entries.async_reload(
                    self.config_entry.entry_id
                )
                return self.async_create_entry(data={})

        # Build schema dynamically based on configured services
        schema_dict: dict[Any, Any] = {}

        if data.get(CONF_RADARR_URL):
            radarr_profiles = data.get(CONF_RADARR_PROFILES, [])
            radarr_folders = data.get(CONF_RADARR_FOLDERS, [])
            if radarr_profiles:
                schema_dict[
                    vol.Optional(
                        CONF_RADARR_QUALITY_PROFILE_ID,
                        default=data.get(CONF_RADARR_QUALITY_PROFILE_ID),
                    )
                ] = SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=str(p["id"]), label=p["name"]
                            )
                            for p in radarr_profiles
                        ]
                    )
                )
            if radarr_folders:
                schema_dict[
                    vol.Optional(
                        CONF_RADARR_ROOT_FOLDER,
                        default=data.get(CONF_RADARR_ROOT_FOLDER),
                    )
                ] = SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=f["path"], label=f["path"]
                            )
                            for f in radarr_folders
                        ]
                    )
                )
            schema_dict[
                vol.Optional(
                    CONF_RADARR_VERIFY_SSL,
                    default=data.get(CONF_RADARR_VERIFY_SSL, True),
                )
            ] = bool

        if data.get(CONF_SONARR_URL):
            sonarr_profiles = data.get(CONF_SONARR_PROFILES, [])
            sonarr_folders = data.get(CONF_SONARR_FOLDERS, [])
            if sonarr_profiles:
                schema_dict[
                    vol.Optional(
                        CONF_SONARR_QUALITY_PROFILE_ID,
                        default=data.get(CONF_SONARR_QUALITY_PROFILE_ID),
                    )
                ] = SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=str(p["id"]), label=p["name"]
                            )
                            for p in sonarr_profiles
                        ]
                    )
                )
            if sonarr_folders:
                schema_dict[
                    vol.Optional(
                        CONF_SONARR_ROOT_FOLDER,
                        default=data.get(CONF_SONARR_ROOT_FOLDER),
                    )
                ] = SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=f["path"], label=f["path"]
                            )
                            for f in sonarr_folders
                        ]
                    )
                )
            schema_dict[
                vol.Optional(
                    CONF_SONARR_VERIFY_SSL,
                    default=data.get(CONF_SONARR_VERIFY_SSL, True),
                )
            ] = bool

        if data.get(CONF_LIDARR_URL):
            lidarr_profiles = data.get(CONF_LIDARR_PROFILES, [])
            lidarr_folders = data.get(CONF_LIDARR_FOLDERS, [])
            lidarr_meta_profiles = data.get(CONF_LIDARR_METADATA_PROFILES, [])
            if lidarr_profiles:
                schema_dict[
                    vol.Optional(
                        CONF_LIDARR_QUALITY_PROFILE_ID,
                        default=data.get(CONF_LIDARR_QUALITY_PROFILE_ID),
                    )
                ] = SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=str(p["id"]), label=p["name"]
                            )
                            for p in lidarr_profiles
                        ]
                    )
                )
            if lidarr_folders:
                schema_dict[
                    vol.Optional(
                        CONF_LIDARR_ROOT_FOLDER,
                        default=data.get(CONF_LIDARR_ROOT_FOLDER),
                    )
                ] = SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=f["path"], label=f["path"]
                            )
                            for f in lidarr_folders
                        ]
                    )
                )
            if lidarr_meta_profiles:
                schema_dict[
                    vol.Optional(
                        CONF_LIDARR_METADATA_PROFILE_ID,
                        default=data.get(CONF_LIDARR_METADATA_PROFILE_ID),
                    )
                ] = SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=str(p["id"]), label=p["name"]
                            )
                            for p in lidarr_meta_profiles
                        ]
                    )
                )
            schema_dict[
                vol.Optional(
                    CONF_LIDARR_VERIFY_SSL,
                    default=data.get(CONF_LIDARR_VERIFY_SSL, True),
                )
            ] = bool

        # Refresh profiles button
        schema_dict[vol.Optional(REFRESH_PROFILES, default=False)] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def _refresh_profiles(
        self, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Re-fetch profiles and folders from all configured arr services."""
        for service_type, url_key, api_key_key, ssl_key in (
            (
                SERVICE_RADARR,
                CONF_RADARR_URL,
                CONF_RADARR_API_KEY,
                CONF_RADARR_VERIFY_SSL,
            ),
            (
                SERVICE_SONARR,
                CONF_SONARR_URL,
                CONF_SONARR_API_KEY,
                CONF_SONARR_VERIFY_SSL,
            ),
            (
                SERVICE_LIDARR,
                CONF_LIDARR_URL,
                CONF_LIDARR_API_KEY,
                CONF_LIDARR_VERIFY_SSL,
            ),
        ):
            url = data.get(url_key)
            if not url:
                continue

            fetched = await _validate_and_fetch(
                self.hass,
                service_type,
                url,
                data[api_key_key],
                data.get(ssl_key, True),
            )

            # Update profiles and folders in data
            prefix = service_type
            data[f"{prefix}_profiles"] = fetched["profiles"]
            data[f"{prefix}_folders"] = fetched["folders"]

            if service_type == SERVICE_LIDARR:
                data[CONF_LIDARR_METADATA_PROFILES] = fetched[
                    "metadata_profiles"
                ]

        return data
