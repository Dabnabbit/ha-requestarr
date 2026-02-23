"""Tests for Requestarr sensor platform."""

from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.requestarr.const import DOMAIN


async def test_sensor_value(hass: HomeAssistant) -> None:
    """Test sensor entity reports correct state from coordinator data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 8080, CONF_API_KEY: "test-key"},
    )
    entry.add_to_hass(hass)

    mock_data = {"status": "ok"}

    with patch(
        "custom_components.requestarr.coordinator.ApiClient.async_get_data",
        new_callable=AsyncMock,
        return_value=mock_data,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(f"sensor.{entry.title.lower().replace(' ', '_')}_status")
    assert state is not None
    assert state.state == "ok"


async def test_sensor_unique_id(hass: HomeAssistant) -> None:
    """Test sensor entity has correct unique_id format."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 8080, CONF_API_KEY: "test-key"},
    )
    entry.add_to_hass(hass)

    mock_data = {"status": "ok"}

    with patch(
        "custom_components.requestarr.coordinator.ApiClient.async_get_data",
        new_callable=AsyncMock,
        return_value=mock_data,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = hass.helpers.entity_registry.async_get(hass)
    entity = entity_registry.async_get(
        f"sensor.{entry.title.lower().replace(' ', '_')}_status"
    )
    assert entity is not None
    assert entity.unique_id == f"{entry.entry_id}_status"


async def test_binary_sensor_online(hass: HomeAssistant) -> None:
    """Test binary sensor shows on when coordinator succeeds."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 8080, CONF_API_KEY: "test-key"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.requestarr.coordinator.ApiClient.async_get_data",
        new_callable=AsyncMock,
        return_value={"status": "ok"},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(
        f"binary_sensor.{entry.title.lower().replace(' ', '_')}_status"
    )
    assert state is not None
    assert state.state == "on"
