"""Common fixtures for the Requestarr tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest


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
