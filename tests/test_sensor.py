"""Tests for Requestarr sensors."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.requestarr.api import ArrClient


async def test_sensor_created_for_configured_services(
    hass: HomeAssistant, radarr_entry
) -> None:
    """Only sensors for configured services are created."""
    radarr_entry.add_to_hass(hass)
    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=10
    ):
        assert await hass.config_entries.async_setup(radarr_entry.entry_id)
        await hass.async_block_till_done()

    # Radarr sensor should exist
    radarr_states = [
        k for k in hass.states.async_entity_ids("sensor")
        if "radarr" in k
    ]
    assert len(radarr_states) >= 1

    # Sonarr/Lidarr sensors should NOT exist (not configured)
    sonarr_states = [
        k for k in hass.states.async_entity_ids("sensor")
        if "sonarr" in k
    ]
    assert len(sonarr_states) == 0


async def test_sensor_library_count_attribute(
    hass: HomeAssistant, radarr_entry
) -> None:
    """Sensor has library_count attribute matching coordinator data."""
    radarr_entry.add_to_hass(hass)
    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=42
    ):
        assert await hass.config_entries.async_setup(radarr_entry.entry_id)
        await hass.async_block_till_done()

    radarr_sensors = [
        k for k in hass.states.async_entity_ids("sensor")
        if "radarr" in k
    ]
    assert radarr_sensors
    state = hass.states.get(radarr_sensors[0])
    assert state is not None
    assert state.attributes.get("library_count") == 42
