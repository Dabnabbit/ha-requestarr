"""Tests for Requestarr coordinator."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.requestarr.api import CannotConnectError
from custom_components.requestarr.const import DOMAIN
from custom_components.requestarr.coordinator import TemplateCoordinator


async def test_coordinator_update(hass: HomeAssistant) -> None:
    """Test successful data refresh from mocked API client."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_API_KEY: "test-key",
        },
    )
    entry.add_to_hass(hass)

    mock_data = {"sensor_value": 42, "status": "ok"}

    with patch(
        "custom_components.requestarr.coordinator.ApiClient.async_get_data",
        new_callable=AsyncMock,
        return_value=mock_data,
    ):
        coordinator = TemplateCoordinator(hass, entry)
        await coordinator.async_refresh()

    assert coordinator.data == mock_data


async def test_coordinator_update_failed(hass: HomeAssistant) -> None:
    """Test failed refresh raises UpdateFailed when API is unreachable."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_API_KEY: "test-key",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.requestarr.coordinator.ApiClient.async_get_data",
        new_callable=AsyncMock,
        side_effect=CannotConnectError("Connection refused"),
    ):
        coordinator = TemplateCoordinator(hass, entry)
        with pytest.raises(UpdateFailed):
            await coordinator.async_refresh()
