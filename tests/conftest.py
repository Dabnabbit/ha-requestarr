"""Common fixtures for the Requestarr tests."""

import asyncio
import threading
from collections.abc import Generator
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Compatibility shim for pytest-homeassistant-custom-component 0.13.205
# bundling HA 2025.1.4, which predates StaticPathConfig (added in HA 2025.7).
# We inject the missing symbol before anything imports the integration.
# ---------------------------------------------------------------------------
import sys

_http_mod = sys.modules.get("homeassistant.components.http")
if _http_mod is not None and not hasattr(_http_mod, "StaticPathConfig"):
    @dataclass
    class _StaticPathConfig:
        url: str
        path: str
        cache_headers: bool = True

    _http_mod.StaticPathConfig = _StaticPathConfig


from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.requestarr.const import (
    DOMAIN,
    CONF_RADARR_URL,
    CONF_RADARR_API_KEY,
    CONF_RADARR_VERIFY_SSL,
    CONF_RADARR_QUALITY_PROFILE_ID,
    CONF_RADARR_ROOT_FOLDER,
    CONF_RADARR_PROFILES,
    CONF_RADARR_FOLDERS,
    CONF_SONARR_URL,
    CONF_SONARR_API_KEY,
    CONF_SONARR_VERIFY_SSL,
    CONF_SONARR_QUALITY_PROFILE_ID,
    CONF_SONARR_ROOT_FOLDER,
    CONF_SONARR_PROFILES,
    CONF_SONARR_FOLDERS,
    CONF_LIDARR_URL,
    CONF_LIDARR_API_KEY,
    CONF_LIDARR_VERIFY_SSL,
    CONF_LIDARR_QUALITY_PROFILE_ID,
    CONF_LIDARR_ROOT_FOLDER,
    CONF_LIDARR_METADATA_PROFILE_ID,
    CONF_LIDARR_PROFILES,
    CONF_LIDARR_FOLDERS,
    CONF_LIDARR_METADATA_PROFILES,
)


@pytest.fixture(autouse=True)
def verify_cleanup(
    event_loop: asyncio.AbstractEventLoop,
    expected_lingering_tasks: bool,
    expected_lingering_timers: bool,
) -> Generator[None]:
    """Override verify_cleanup to tolerate daemon threads from pycares/aiodns.

    pytest-homeassistant-custom-component 0.13.205 (bundling HA 2025.1.4) does
    not allow daemon threads in the thread cleanup check. However, pycares (used
    by aiohttp's aiodns resolver) creates a daemon Thread named
    '_run_safe_shutdown_loop' when a DNS channel is destroyed. This override
    relaxes the assertion to permit daemon threads, while keeping all other
    cleanup checks intact.
    """
    from pytest_homeassistant_custom_component.plugins import (
        INSTANCES,
        get_scheduled_timer_handles,
        long_repr_strings,
    )
    from homeassistant.helpers.event import HassJob

    threads_before = frozenset(threading.enumerate())
    tasks_before = asyncio.all_tasks(event_loop)
    yield

    event_loop.run_until_complete(event_loop.shutdown_default_executor())

    if len(INSTANCES) >= 2:
        count = len(INSTANCES)
        for inst in INSTANCES:
            inst.stop()
        pytest.exit(f"Detected non stopped instances ({count}), aborting test run")

    tasks = asyncio.all_tasks(event_loop) - tasks_before
    for task in tasks:
        if expected_lingering_tasks:
            pass  # tolerated
        else:
            pytest.fail(f"Lingering task after test {task!r}")
        task.cancel()
    if tasks:
        event_loop.run_until_complete(asyncio.wait(tasks))

    for handle in get_scheduled_timer_handles(event_loop):
        if not handle.cancelled():
            with long_repr_strings():
                if expected_lingering_timers:
                    pass  # tolerated
                elif handle._args and isinstance(job := handle._args[-1], HassJob):
                    if job.cancel_on_shutdown:
                        continue
                    pytest.fail(f"Lingering timer after job {job!r}")
                else:
                    pytest.fail(f"Lingering timer after test {handle!r}")
                handle.cancel()

    # Check for unexpected threads — allow daemon threads (e.g. pycares DNS resolver).
    threads = frozenset(threading.enumerate()) - threads_before
    for thread in threads:
        assert (
            isinstance(thread, threading._DummyThread)
            or thread.name.startswith("waitpid-")
            or thread.daemon  # pycares aiodns safe-shutdown thread
        ), f"Unexpected non-daemon thread: {thread!r}"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests in this package."""
    yield


@pytest.fixture(autouse=True)
def mock_http_server():
    """Prevent aiohttp HTTP server from creating a real server thread.

    The http component starts a real TCP server which spawns a
    '_run_safe_shutdown_loop' thread. The test framework's verify_cleanup
    fixture asserts no unexpected threads remain, causing a teardown error.
    Preventing the server from actually binding avoids this.
    """
    with patch(
        "homeassistant.components.http.start_http_server_and_save_config",
        new_callable=AsyncMock,
        return_value=None,
    ):
        yield


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry (and async_setup) to prevent full integration setup during config flow tests."""
    with patch(
        "custom_components.requestarr.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry, patch(
        "custom_components.requestarr.async_setup",
        return_value=True,
    ):
        yield mock_setup_entry


@pytest.fixture
def radarr_entry() -> MockConfigEntry:
    """Config entry with only Radarr configured."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={
            CONF_RADARR_URL: "http://192.168.1.50:7878",
            CONF_RADARR_API_KEY: "radarr-test-key",
            CONF_RADARR_VERIFY_SSL: True,
            CONF_RADARR_QUALITY_PROFILE_ID: 1,
            CONF_RADARR_ROOT_FOLDER: "/movies",
            CONF_RADARR_PROFILES: [{"id": 1, "name": "HD-1080p"}],
            CONF_RADARR_FOLDERS: [{"id": 1, "path": "/movies"}],
        },
    )


@pytest.fixture
def sonarr_entry() -> MockConfigEntry:
    """Config entry with only Sonarr configured."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={
            CONF_SONARR_URL: "http://192.168.1.50:8989",
            CONF_SONARR_API_KEY: "sonarr-test-key",
            CONF_SONARR_VERIFY_SSL: True,
            CONF_SONARR_QUALITY_PROFILE_ID: 2,
            CONF_SONARR_ROOT_FOLDER: "/tv",
            CONF_SONARR_PROFILES: [{"id": 2, "name": "HD-1080p"}],
            CONF_SONARR_FOLDERS: [{"id": 1, "path": "/tv"}],
        },
    )


@pytest.fixture
def lidarr_entry() -> MockConfigEntry:
    """Config entry with only Lidarr configured."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={
            CONF_LIDARR_URL: "http://192.168.1.50:8686",
            CONF_LIDARR_API_KEY: "lidarr-test-key",
            CONF_LIDARR_VERIFY_SSL: True,
            CONF_LIDARR_QUALITY_PROFILE_ID: 1,
            CONF_LIDARR_ROOT_FOLDER: "/music",
            CONF_LIDARR_METADATA_PROFILE_ID: 1,
            CONF_LIDARR_PROFILES: [{"id": 1, "name": "Lossless"}],
            CONF_LIDARR_FOLDERS: [{"id": 1, "path": "/music"}],
            CONF_LIDARR_METADATA_PROFILES: [{"id": 1, "name": "Standard"}],
        },
    )


@pytest.fixture
def all_services_entry() -> MockConfigEntry:
    """Config entry with all three arr services configured."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={
            CONF_RADARR_URL: "http://192.168.1.50:7878",
            CONF_RADARR_API_KEY: "radarr-test-key",
            CONF_RADARR_VERIFY_SSL: True,
            CONF_RADARR_QUALITY_PROFILE_ID: 1,
            CONF_RADARR_ROOT_FOLDER: "/movies",
            CONF_RADARR_PROFILES: [{"id": 1, "name": "HD-1080p"}],
            CONF_RADARR_FOLDERS: [{"id": 1, "path": "/movies"}],
            CONF_SONARR_URL: "http://192.168.1.50:8989",
            CONF_SONARR_API_KEY: "sonarr-test-key",
            CONF_SONARR_VERIFY_SSL: True,
            CONF_SONARR_QUALITY_PROFILE_ID: 2,
            CONF_SONARR_ROOT_FOLDER: "/tv",
            CONF_SONARR_PROFILES: [{"id": 2, "name": "HD-1080p"}],
            CONF_SONARR_FOLDERS: [{"id": 1, "path": "/tv"}],
            CONF_LIDARR_URL: "http://192.168.1.50:8686",
            CONF_LIDARR_API_KEY: "lidarr-test-key",
            CONF_LIDARR_VERIFY_SSL: True,
            CONF_LIDARR_QUALITY_PROFILE_ID: 1,
            CONF_LIDARR_ROOT_FOLDER: "/music",
            CONF_LIDARR_METADATA_PROFILE_ID: 1,
            CONF_LIDARR_PROFILES: [{"id": 1, "name": "Lossless"}],
            CONF_LIDARR_FOLDERS: [{"id": 1, "path": "/music"}],
            CONF_LIDARR_METADATA_PROFILES: [{"id": 1, "name": "Standard"}],
        },
    )
