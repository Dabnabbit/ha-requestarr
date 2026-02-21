"""Tests for Requestarr WebSocket commands."""

from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.requestarr.const import DOMAIN


async def test_websocket_get_data(hass: HomeAssistant, hass_ws_client) -> None:
    """Test the WebSocket get_data command returns coordinator data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 8080, CONF_API_KEY: "test-key"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.requestarr.coordinator.ApiClient.async_get_data",
        new_callable=AsyncMock,
        return_value={"sensor_value": 42},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": f"{DOMAIN}/get_data"})
    result = await client.receive_json()

    assert result["success"] is True
    assert result["result"] == {"sensor_value": 42}
