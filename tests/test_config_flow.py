"""Tests for Requestarr config flow."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.requestarr.const import (
    DOMAIN,
    CONF_RADARR_URL,
    CONF_RADARR_API_KEY,
    CONF_RADARR_VERIFY_SSL,
)
from custom_components.requestarr.config_flow import (
    SKIP_RADARR,
    SKIP_SONARR,
    SKIP_LIDARR,
)


@pytest.fixture
def mock_validate():
    """Patch ArrClient.async_validate_connection to succeed silently."""
    with patch(
        "custom_components.requestarr.config_flow.ArrClient.async_validate_connection",
        new_callable=AsyncMock,
        return_value=None,
    ) as m:
        yield m


@pytest.fixture
def mock_profiles():
    """Patch profile/folder/metadata fetches to return minimal data."""
    with (
        patch(
            "custom_components.requestarr.config_flow.ArrClient.async_get_quality_profiles",
            new_callable=AsyncMock,
            return_value=[{"id": 1, "name": "HD-1080p"}],
        ),
        patch(
            "custom_components.requestarr.config_flow.ArrClient.async_get_root_folders",
            new_callable=AsyncMock,
            return_value=[{"id": 1, "path": "/data"}],
        ),
        patch(
            "custom_components.requestarr.config_flow.ArrClient.async_get_metadata_profiles",
            new_callable=AsyncMock,
            return_value=[{"id": 1, "name": "Standard"}],
        ),
    ):
        yield


async def test_config_flow_radarr_only(
    hass: HomeAssistant, mock_setup_entry, mock_validate, mock_profiles
) -> None:
    """Configure Radarr only; skip Sonarr and Lidarr."""
    # Step 1: Radarr
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "radarr"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_RADARR_URL: "http://192.168.1.50:7878",
            CONF_RADARR_API_KEY: "radarr-key",
            CONF_RADARR_VERIFY_SSL: True,
            SKIP_RADARR: False,
        },
    )
    # Step 2: Sonarr — skip it
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sonarr"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {SKIP_SONARR: True},
    )
    # Step 3: Lidarr — skip it
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "lidarr"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {SKIP_LIDARR: True},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_RADARR_URL] == "http://192.168.1.50:7878"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_config_flow_cannot_connect(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """Connection failure in Radarr step shows error and stays on radarr form."""
    from custom_components.requestarr.api import CannotConnectError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.requestarr.config_flow.ArrClient.async_validate_connection",
        new_callable=AsyncMock,
        side_effect=CannotConnectError("refused"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_RADARR_URL: "http://bad-host:7878",
                CONF_RADARR_API_KEY: "bad-key",
                CONF_RADARR_VERIFY_SSL: True,
                SKIP_RADARR: False,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "radarr"
    # CannotConnectError keys the error to the URL field, not "base"
    assert CONF_RADARR_URL in result["errors"] or "base" in result["errors"]


async def test_config_flow_abort_already_configured(
    hass: HomeAssistant, radarr_entry, mock_validate, mock_profiles
) -> None:
    """Config flow aborts when integration already configured (unique_id = DOMAIN).

    The abort check happens in _create_entry (the final step), after all three
    form steps complete. unique_id = DOMAIN means only one Requestarr instance allowed.
    """
    radarr_entry.add_to_hass(hass)

    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "radarr"

    # Submit Radarr
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_RADARR_URL: "http://192.168.1.50:7878",
            CONF_RADARR_API_KEY: "radarr-key",
            CONF_RADARR_VERIFY_SSL: True,
            SKIP_RADARR: False,
        },
    )
    assert result["step_id"] == "sonarr"

    # Skip Sonarr
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {SKIP_SONARR: True},
    )
    assert result["step_id"] == "lidarr"

    # Skip Lidarr — triggers _create_entry → _abort_if_unique_id_configured
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {SKIP_LIDARR: True},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
