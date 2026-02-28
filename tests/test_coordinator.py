"""Tests for Requestarr coordinator."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.requestarr.api import ArrClient, CannotConnectError
from custom_components.requestarr.coordinator import RequestarrCoordinator


async def test_coordinator_single_service_update(
    hass: HomeAssistant, radarr_entry
) -> None:
    """Coordinator polls Radarr library count successfully."""
    radarr_entry.add_to_hass(hass)
    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=42
    ):
        coordinator = RequestarrCoordinator(hass, radarr_entry)
        await coordinator.async_refresh()

    assert coordinator.data["radarr_count"] == 42
    assert "sonarr_count" not in coordinator.data


async def test_coordinator_partial_failure(
    hass: HomeAssistant, all_services_entry
) -> None:
    """Radarr fails but Sonarr and Lidarr succeed — coordinator data still valid."""
    all_services_entry.add_to_hass(hass)
    call_count = 0

    async def mock_count(self):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise CannotConnectError("Radarr down")
        return 10

    with patch.object(ArrClient, "async_get_library_count", new=mock_count):
        coordinator = RequestarrCoordinator(hass, all_services_entry)
        await coordinator.async_refresh()

    assert coordinator.data["radarr_count"] is None
    assert coordinator.data.get("sonarr_count") == 10
    # UpdateFailed NOT raised — partial failure is tolerated


async def test_coordinator_all_services_fail(
    hass: HomeAssistant, radarr_entry
) -> None:
    """When all configured services fail, coordinator marks last_update_success False.

    async_refresh() catches UpdateFailed internally and stores the failure state,
    so we verify through coordinator.last_update_success and last_exception.
    """
    radarr_entry.add_to_hass(hass)
    with patch.object(
        ArrClient,
        "async_get_library_count",
        new_callable=AsyncMock,
        side_effect=CannotConnectError("down"),
    ):
        coordinator = RequestarrCoordinator(hass, radarr_entry)
        await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    assert isinstance(coordinator.last_exception, UpdateFailed)


async def test_coordinator_get_client(hass: HomeAssistant, radarr_entry) -> None:
    """get_client returns ArrClient for configured services, None for unconfigured."""
    radarr_entry.add_to_hass(hass)
    coordinator = RequestarrCoordinator(hass, radarr_entry)

    assert coordinator.get_client("radarr") is not None
    assert coordinator.get_client("sonarr") is None
    assert coordinator.get_client("lidarr") is None
