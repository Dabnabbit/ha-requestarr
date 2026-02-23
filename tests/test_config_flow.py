"""Tests for Requestarr config flow."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.requestarr.config_flow import CannotConnect
from custom_components.requestarr.const import DOMAIN


async def test_form(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test the user config flow form — successful setup."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.requestarr.config_flow._async_validate_connection",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 8080,
                CONF_API_KEY: "test-key",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == "192.168.1.100"
    assert result["data"][CONF_PORT] == 8080
    assert result["data"][CONF_API_KEY] == "test-key"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test the config flow form — connection failure shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    with patch(
        "custom_components.requestarr.config_flow._async_validate_connection",
        side_effect=CannotConnect,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 8080,
                CONF_API_KEY: "test-key",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_duplicate_abort(hass: HomeAssistant) -> None:
    """Test the config flow aborts when the same host:port is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:8080",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_API_KEY: "existing-key",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    with patch(
        "custom_components.requestarr.config_flow._async_validate_connection",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 8080,
                CONF_API_KEY: "test-key",
            },
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test the options flow validates, updates entry.data, and reloads."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_API_KEY: "old-key",
        },
    )
    entry.add_to_hass(hass)

    # Mock setup/unload so reload succeeds
    with (
        patch(
            "custom_components.requestarr.async_setup_entry",
            return_value=True,
        ),
        patch(
            "custom_components.requestarr.async_unload_entry",
            return_value=True,
        ),
        patch(
            "custom_components.requestarr.config_flow._async_validate_connection",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.1.200",
                CONF_PORT: 8080,
                CONF_API_KEY: "new-key",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_HOST] == "192.168.1.200"
    assert entry.data[CONF_API_KEY] == "new-key"


async def test_options_flow_error(hass: HomeAssistant) -> None:
    """Test the options flow shows errors on validation failure without reloading."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_API_KEY: "old-key",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.requestarr.config_flow._async_validate_connection",
        side_effect=CannotConnect,
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "bad-host",
                CONF_PORT: 8080,
                CONF_API_KEY: "old-key",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    # Original data unchanged
    assert entry.data[CONF_HOST] == "192.168.1.100"
