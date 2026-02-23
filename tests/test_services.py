"""Tests for Requestarr service handlers."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.requestarr.const import DOMAIN


async def test_query_service(hass: HomeAssistant) -> None:
    """Test the query service returns coordinator data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 8080, CONF_API_KEY: "test-key"},
    )
    entry.add_to_hass(hass)

    mock_data = {"sensor_value": 42, "status": "ok"}

    with patch(
        "custom_components.requestarr.coordinator.ApiClient.async_get_data",
        new_callable=AsyncMock,
        return_value=mock_data,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.services.async_call(
        DOMAIN,
        "query",
        {"query": "test"},
        blocking=True,
        return_response=True,
    )

    assert result is not None
    assert result["query"] == "test"


async def test_query_service_no_entry(hass: HomeAssistant) -> None:
    """Test the query service raises when no config entry exists."""
    # Register services without a config entry
    from custom_components.requestarr.services import async_register_services

    async_register_services(hass)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "query",
            {"query": "test"},
            blocking=True,
            return_response=True,
        )
