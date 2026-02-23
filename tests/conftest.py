"""Common fixtures for the Requestarr tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.requestarr.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests in this package."""
    yield


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry to prevent full integration setup during config flow tests."""
    with patch(
        "custom_components.requestarr.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry for tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_API_KEY: "test-key",
        },
    )
