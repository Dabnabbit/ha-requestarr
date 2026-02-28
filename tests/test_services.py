"""Tests for Requestarr service handlers."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.requestarr.api import ArrClient


async def test_query_service(hass: HomeAssistant, radarr_entry) -> None:
    """Test the query service returns coordinator data plus query."""
    radarr_entry.add_to_hass(hass)

    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=10
    ):
        assert await hass.config_entries.async_setup(radarr_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.services.async_call(
        "requestarr",
        "query",
        {"query": "test"},
        blocking=True,
        return_response=True,
    )

    assert result is not None
    assert result["query"] == "test"


async def test_query_service_no_entry(hass: HomeAssistant) -> None:
    """Test the query service raises when no config entry exists."""
    from custom_components.requestarr.services import async_register_services

    async_register_services(hass)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "requestarr",
            "query",
            {"query": "test"},
            blocking=True,
            return_response=True,
        )
