"""WebSocket API for the Requestarr integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .api import CannotConnectError, InvalidAuthError, ServerError
from .const import (
    ARR_SERVICES,
    CONF_LIDARR_METADATA_PROFILE_ID,
    CONF_LIDARR_METADATA_PROFILES,
    CONF_LIDARR_QUALITY_PROFILE_ID,
    CONF_LIDARR_ROOT_FOLDER,
    CONF_LIDARR_PROFILES,
    CONF_LIDARR_FOLDERS,
    CONF_RADARR_QUALITY_PROFILE_ID,
    CONF_RADARR_ROOT_FOLDER,
    CONF_RADARR_PROFILES,
    CONF_RADARR_FOLDERS,
    CONF_SONARR_QUALITY_PROFILE_ID,
    CONF_SONARR_ROOT_FOLDER,
    CONF_SONARR_PROFILES,
    CONF_SONARR_FOLDERS,
    DOMAIN,
    MAX_SEARCH_RESULTS,
    SERVICE_LIDARR,
    SERVICE_RADARR,
    SERVICE_SONARR,
    WS_TYPE_GET_QUEUE,
    WS_TYPE_GET_SERIES_SEASONS,
    WS_TYPE_GET_ARTIST_ALBUMS,
    WS_TYPE_REQUEST_ALBUM,
    WS_TYPE_REQUEST_ARTIST,
    WS_TYPE_REQUEST_MOVIE,
    WS_TYPE_REQUEST_TV,
    WS_TYPE_SEARCH_MOVIES,
    WS_TYPE_SEARCH_MUSIC,
    WS_TYPE_SEARCH_TV,
)

_LOGGER = logging.getLogger(__name__)

WS_TYPE_GET_DATA = f"{DOMAIN}/get_data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_coordinator(hass: HomeAssistant):
    """Return the RequestarrCoordinator, or None if not configured."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return None
    return entries[0].runtime_data.coordinator


def _get_config_data(hass: HomeAssistant) -> dict[str, Any]:
    """Return the config entry data dict, or empty dict."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return {}
    return dict(entries[0].data)


def _resolve_profile_name(
    profiles: list[dict[str, Any]], profile_id: Any
) -> str:
    """Look up a quality/metadata profile name by ID from stored profiles list."""
    if not profiles or profile_id is None:
        return ""
    # profile_id might be stored as int or str depending on options flow
    for profile in profiles:
        if str(profile.get("id")) == str(profile_id):
            return profile.get("name", "")
    return ""


# ---------------------------------------------------------------------------
# Result normalization
# ---------------------------------------------------------------------------


def _extract_poster_url(
    item: dict[str, Any], cover_type: str = "poster"
) -> str | None:
    """Extract poster URL from arr lookup result.

    Prefers remotePoster/remoteCover top-level field, falls back to images
    array matching the specified cover type and using the remoteUrl field.
    """
    poster_url = item.get("remotePoster") or item.get("remoteCover")

    if not poster_url and "images" in item:
        for img in item.get("images", []):
            if img.get("coverType") == cover_type:
                poster_url = img.get("remoteUrl")
                break

    return poster_url


def _rewrite_tmdb_poster(url: str | None) -> str | None:
    """Rewrite TMDB image URLs from /original/ to /w300/ for faster loading.

    TheTVDB and fanart.tv URLs are passed through unchanged.
    """
    if url and "image.tmdb.org/t/p/original" in url:
        return url.replace("/t/p/original/", "/t/p/w300/")
    return url


def _normalize_movie_result(
    item: dict[str, Any], config_data: dict[str, Any]
) -> dict[str, Any]:
    """Normalize a Radarr movie lookup result into a standard search result."""
    poster_url = _rewrite_tmdb_poster(_extract_poster_url(item))
    arr_id = item.get("id", 0)

    return {
        "title": item.get("title", ""),
        "year": item.get("year"),
        "overview": item.get("overview", ""),
        "poster_url": poster_url,
        "in_library": arr_id > 0,
        "arr_id": arr_id if arr_id > 0 else None,
        "tmdb_id": item.get("tmdbId"),
        "title_slug": item.get("titleSlug", ""),
        "has_file": item.get("hasFile", False),
        "quality_profile": _resolve_profile_name(
            config_data.get(CONF_RADARR_PROFILES, []),
            config_data.get(CONF_RADARR_QUALITY_PROFILE_ID),
        ),
        "root_folder": config_data.get(CONF_RADARR_ROOT_FOLDER, ""),
    }


def _normalize_tv_result(
    item: dict[str, Any], config_data: dict[str, Any]
) -> dict[str, Any]:
    """Normalize a Sonarr series lookup result into a standard search result."""
    poster_url = _extract_poster_url(item)
    # TheTVDB URLs pass through unchanged (no rewriting needed)
    arr_id = item.get("id", 0)

    return {
        "title": item.get("title", ""),
        "year": item.get("year"),
        "overview": item.get("overview", ""),
        "poster_url": poster_url,
        "in_library": arr_id > 0,
        "arr_id": arr_id if arr_id > 0 else None,
        "tvdb_id": item.get("tvdbId"),
        "title_slug": item.get("titleSlug", ""),
        "has_file": False,  # Sonarr lookup statistics always 0 (issue #4942)
        "seasons": item.get("seasons", []),  # pass raw seasons list through
        "quality_profile": _resolve_profile_name(
            config_data.get(CONF_SONARR_PROFILES, []),
            config_data.get(CONF_SONARR_QUALITY_PROFILE_ID),
        ),
        "root_folder": config_data.get(CONF_SONARR_ROOT_FOLDER, ""),
    }


def _normalize_music_result(
    item: dict[str, Any], config_data: dict[str, Any]
) -> dict[str, Any]:
    """Normalize a Lidarr artist lookup result into a standard search result."""
    poster_url = _extract_poster_url(item)
    # fanart.tv URLs pass through unchanged (no rewriting needed)
    arr_id = item.get("id", 0)

    return {
        "title": item.get("artistName", ""),
        "year": None,  # Artists don't have a single release year
        "overview": item.get("overview", ""),
        "poster_url": poster_url,
        "in_library": arr_id > 0,
        "arr_id": arr_id if arr_id > 0 else None,
        "foreign_artist_id": item.get("foreignArtistId"),
        "quality_profile": _resolve_profile_name(
            config_data.get(CONF_LIDARR_PROFILES, []),
            config_data.get(CONF_LIDARR_QUALITY_PROFILE_ID),
        ),
        "metadata_profile": _resolve_profile_name(
            config_data.get(CONF_LIDARR_METADATA_PROFILES, []),
            config_data.get(CONF_LIDARR_METADATA_PROFILE_ID),
        ),
        "root_folder": config_data.get(CONF_LIDARR_ROOT_FOLDER, ""),
    }


# ---------------------------------------------------------------------------
# Generic search handler
# ---------------------------------------------------------------------------


async def _handle_search(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    service_type: str,
    normalize_fn: Any,
) -> None:
    """Generic search handler for all arr services.

    Validates query, checks service configuration, calls arr lookup,
    normalizes results, and sends response.
    """
    query = msg["query"].strip()
    if not query:
        connection.send_result(
            msg["id"],
            {
                "error": "invalid_query",
                "message": "Search query cannot be empty",
                "results": [],
            },
        )
        return

    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(
            msg["id"], "not_found", "Requestarr not configured"
        )
        return

    client = coordinator.get_client(service_type)
    if client is None:
        connection.send_result(
            msg["id"],
            {
                "error": "service_not_configured",
                "message": (
                    f"{service_type.title()} is not configured in Requestarr"
                ),
                "results": [],
            },
        )
        return

    config_data = _get_config_data(hass)

    try:
        raw_results = await client.async_search(query)
    except (CannotConnectError, InvalidAuthError, ServerError) as err:
        _LOGGER.warning(
            "Search failed for %s: %s", service_type, err
        )
        connection.send_result(
            msg["id"],
            {
                "error": "service_unavailable",
                "message": (
                    f"{service_type.title()} is unavailable: {err}"
                ),
                "results": [],
            },
        )
        return

    results = [
        normalize_fn(item, config_data)
        for item in raw_results[:MAX_SEARCH_RESULTS]
    ]
    connection.send_result(msg["id"], {"results": results})


# ---------------------------------------------------------------------------
# WebSocket command handlers
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_GET_DATA,
    }
)
@websocket_api.async_response
async def websocket_get_data(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle get_data WebSocket command for Requestarr."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "No config entries"
        )
        return

    coordinator = entries[0].runtime_data.coordinator
    connection.send_result(msg["id"], coordinator.data or {})


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_SEARCH_MOVIES,
        vol.Required("query"): str,
    }
)
@websocket_api.async_response
async def websocket_search_movies(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle movie search via Radarr lookup endpoint."""
    await _handle_search(
        hass, connection, msg, SERVICE_RADARR, _normalize_movie_result
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_SEARCH_TV,
        vol.Required("query"): str,
    }
)
@websocket_api.async_response
async def websocket_search_tv(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle TV series search via Sonarr lookup endpoint.

    For series already in the library, fetches accurate season statistics
    from /series/{id} so that episodeFileCount is reliable for per-season
    in-library display. The lookup endpoint does not populate episodeFileCount.
    """
    query = msg["query"].strip()
    if not query:
        connection.send_result(
            msg["id"],
            {
                "error": "invalid_query",
                "message": "Search query cannot be empty",
                "results": [],
            },
        )
        return

    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Requestarr not configured")
        return

    client = coordinator.get_client(SERVICE_SONARR)
    if client is None:
        connection.send_result(
            msg["id"],
            {
                "error": "service_not_configured",
                "message": "Sonarr is not configured in Requestarr",
                "results": [],
            },
        )
        return

    config_data = _get_config_data(hass)

    try:
        raw_results = await client.async_search(query)
    except (CannotConnectError, InvalidAuthError, ServerError) as err:
        _LOGGER.warning("Search failed for sonarr: %s", err)
        connection.send_result(
            msg["id"],
            {
                "error": "service_unavailable",
                "message": f"Sonarr is unavailable: {err}",
                "results": [],
            },
        )
        return

    results = []
    for item in raw_results[:MAX_SEARCH_RESULTS]:
        normalized = _normalize_tv_result(item, config_data)
        # Enrich in-library results with accurate season stats from /series/{id}.
        # The lookup endpoint does not populate statistics.episodeFileCount, so
        # per-season library status would be unreliable without this extra call.
        if normalized["arr_id"] is not None:
            try:
                accurate_seasons = await client.async_get_series_seasons(
                    normalized["arr_id"]
                )
                if accurate_seasons:
                    normalized["seasons"] = accurate_seasons
            except (CannotConnectError, InvalidAuthError, ServerError):
                pass  # keep lookup seasons as fallback
        results.append(normalized)

    connection.send_result(msg["id"], {"results": results})


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_SEARCH_MUSIC,
        vol.Required("query"): str,
    }
)
@websocket_api.async_response
async def websocket_search_music(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle music artist search via Lidarr lookup endpoint."""
    await _handle_search(
        hass, connection, msg, SERVICE_LIDARR, _normalize_music_result
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_REQUEST_MOVIE,
        vol.Required("tmdb_id"): int,
        vol.Required("title"): str,
        vol.Required("title_slug"): str,
    }
)
@websocket_api.async_response
async def websocket_request_movie(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle movie request via Radarr POST."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "not_configured",
                "message": "Requestarr not configured",
            },
        )
        return

    client = coordinator.get_client(SERVICE_RADARR)
    if client is None:
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "service_not_configured",
                "message": "Radarr is not configured",
            },
        )
        return

    config_data = _get_config_data(hass)
    quality_profile_id = config_data.get(CONF_RADARR_QUALITY_PROFILE_ID)
    root_folder = config_data.get(CONF_RADARR_ROOT_FOLDER, "")

    try:
        await client.async_request_movie(
            tmdb_id=msg["tmdb_id"],
            title=msg["title"],
            title_slug=msg["title_slug"],
            quality_profile_id=quality_profile_id,
            root_folder_path=root_folder,
        )
        connection.send_result(msg["id"], {"success": True})
    except ServerError as err:
        err_str = str(err)
        # Radarr 400 on the add endpoint means the movie is already in the library
        if "400" in err_str and "already been added" in err_str.lower():
            connection.send_result(
                msg["id"],
                {
                    "success": False,
                    "error_code": "already_exists",
                    "message": "This movie is already in Radarr",
                },
            )
        else:
            _LOGGER.warning("Movie request failed: %s", err)
            connection.send_result(
                msg["id"],
                {
                    "success": False,
                    "error_code": "service_unavailable",
                    "message": str(err),
                },
            )
    except (CannotConnectError, InvalidAuthError) as err:
        _LOGGER.warning("Movie request failed: %s", err)
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "service_unavailable",
                "message": str(err),
            },
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_REQUEST_TV,
        vol.Required("tvdb_id"): int,
        vol.Required("title"): str,
        vol.Required("title_slug"): str,
        vol.Required("seasons"): list,
        vol.Optional("arr_id"): int,
    }
)
@websocket_api.async_response
async def websocket_request_series(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle TV series request via Sonarr POST."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "not_configured",
                "message": "Requestarr not configured",
            },
        )
        return

    client = coordinator.get_client(SERVICE_SONARR)
    if client is None:
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "service_not_configured",
                "message": "Sonarr is not configured",
            },
        )
        return

    config_data = _get_config_data(hass)
    quality_profile_id = config_data.get(CONF_SONARR_QUALITY_PROFILE_ID)
    root_folder = config_data.get(CONF_SONARR_ROOT_FOLDER, "")

    arr_id = msg.get("arr_id")

    try:
        if arr_id:
            # Series already in Sonarr — monitor requested seasons and trigger search
            season_numbers = [
                s.get("seasonNumber", 0)
                for s in msg["seasons"]
                if s.get("monitored", False)
            ]
            await client.async_monitor_seasons(arr_id, season_numbers)
        else:
            await client.async_request_series(
                tvdb_id=msg["tvdb_id"],
                title=msg["title"],
                title_slug=msg["title_slug"],
                quality_profile_id=quality_profile_id,
                root_folder_path=root_folder,
                seasons=msg["seasons"],
            )
        connection.send_result(msg["id"], {"success": True})
    except ServerError as err:
        err_str = str(err)
        # Sonarr 400 on the add endpoint means the series is already in the library
        if "400" in err_str and "already been added" in err_str.lower():
            connection.send_result(
                msg["id"],
                {
                    "success": False,
                    "error_code": "already_exists",
                    "message": "This series is already in Sonarr",
                },
            )
        else:
            _LOGGER.warning("Series request failed: %s", err)
            connection.send_result(
                msg["id"],
                {
                    "success": False,
                    "error_code": "service_unavailable",
                    "message": str(err),
                },
            )
    except (CannotConnectError, InvalidAuthError) as err:
        _LOGGER.warning("Series request failed: %s", err)
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "service_unavailable",
                "message": str(err),
            },
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_REQUEST_ARTIST,
        vol.Required("foreign_artist_id"): str,   # MusicBrainz UUID string
        vol.Required("title"): str,               # artist name (for logging)
    }
)
@websocket_api.async_response
async def websocket_request_artist(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle music artist request via Lidarr POST."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "not_configured",
                "message": "Requestarr not configured",
            },
        )
        return

    client = coordinator.get_client(SERVICE_LIDARR)
    if client is None:
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "service_not_configured",
                "message": "Lidarr is not configured",
            },
        )
        return

    config_data = _get_config_data(hass)
    quality_profile_id = config_data.get(CONF_LIDARR_QUALITY_PROFILE_ID)
    metadata_profile_id = config_data.get(CONF_LIDARR_METADATA_PROFILE_ID)
    root_folder = config_data.get(CONF_LIDARR_ROOT_FOLDER, "")

    try:
        await client.async_request_artist(
            foreign_artist_id=msg["foreign_artist_id"],
            artist_name=msg["title"],
            quality_profile_id=quality_profile_id,
            metadata_profile_id=metadata_profile_id,
            root_folder_path=root_folder,
        )
        connection.send_result(msg["id"], {"success": True})
    except ServerError as err:
        err_str = str(err)
        # Lidarr 400 on the add endpoint means the artist is already in the library
        if "400" in err_str and "already been added" in err_str.lower():
            connection.send_result(
                msg["id"],
                {
                    "success": False,
                    "error_code": "already_exists",
                    "message": "This artist is already in Lidarr",
                },
            )
        else:
            _LOGGER.warning("Artist request failed: %s", err)
            connection.send_result(
                msg["id"],
                {
                    "success": False,
                    "error_code": "service_unavailable",
                    "message": str(err),
                },
            )
    except (CannotConnectError, InvalidAuthError) as err:
        _LOGGER.warning("Artist request failed: %s", err)
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "service_unavailable",
                "message": str(err),
            },
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_GET_SERIES_SEASONS,
        vol.Required("arr_id"): int,
    }
)
@websocket_api.async_response
async def websocket_get_series_seasons(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle get_series_seasons — fetch accurate season data from Sonarr library."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Requestarr not configured")
        return

    client = coordinator.get_client(SERVICE_SONARR)
    if client is None:
        connection.send_error(msg["id"], "not_found", "Sonarr is not configured")
        return

    try:
        seasons = await client.async_get_series_seasons(arr_id=msg["arr_id"])
        connection.send_result(msg["id"], {"seasons": seasons})
    except (CannotConnectError, InvalidAuthError, ServerError) as err:
        _LOGGER.warning("get_series_seasons failed: %s", err)
        connection.send_result(msg["id"], {"seasons": [], "error": str(err)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_GET_ARTIST_ALBUMS,
        vol.Required("foreign_artist_id"): str,
        vol.Optional("arr_id"): int,
    }
)
@websocket_api.async_response
async def websocket_get_artist_albums(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle get_artist_albums WebSocket command — fetch Lidarr album list."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Requestarr not configured")
        return

    client = coordinator.get_client(SERVICE_LIDARR)
    if client is None:
        connection.send_error(msg["id"], "not_found", "Lidarr is not configured")
        return

    try:
        albums = await client.async_get_artist_albums(
            foreign_artist_id=msg["foreign_artist_id"],
            arr_id=msg.get("arr_id"),
        )
        connection.send_result(msg["id"], {"albums": albums})
    except (CannotConnectError, InvalidAuthError, ServerError) as err:
        _LOGGER.warning("get_artist_albums failed: %s", err)
        connection.send_result(msg["id"], {"albums": [], "error": str(err)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_REQUEST_ALBUM,
        vol.Required("foreign_artist_id"): str,
        vol.Required("foreign_album_id"): str,
        vol.Required("title"): str,
    }
)
@websocket_api.async_response
async def websocket_request_album(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle single album request via Lidarr POST."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "not_configured",
                "message": "Requestarr not configured",
            },
        )
        return

    client = coordinator.get_client(SERVICE_LIDARR)
    if client is None:
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "service_not_configured",
                "message": "Lidarr is not configured",
            },
        )
        return

    config_data = _get_config_data(hass)
    quality_profile_id = config_data.get(CONF_LIDARR_QUALITY_PROFILE_ID)
    metadata_profile_id = config_data.get(CONF_LIDARR_METADATA_PROFILE_ID)
    root_folder = config_data.get(CONF_LIDARR_ROOT_FOLDER, "")

    try:
        await client.async_request_album(
            foreign_artist_id=msg["foreign_artist_id"],
            foreign_album_id=msg["foreign_album_id"],
            artist_name=msg["title"],
            quality_profile_id=quality_profile_id,
            metadata_profile_id=metadata_profile_id,
            root_folder_path=root_folder,
        )
        connection.send_result(msg["id"], {"success": True})
    except ServerError as err:
        err_str = str(err)
        if "400" in err_str and "already been added" in err_str.lower():
            connection.send_result(
                msg["id"],
                {
                    "success": False,
                    "error_code": "already_exists",
                    "message": "This artist is already in Lidarr",
                },
            )
        else:
            _LOGGER.warning("Album request failed: %s", err)
            connection.send_result(
                msg["id"],
                {
                    "success": False,
                    "error_code": "service_unavailable",
                    "message": str(err),
                },
            )
    except (CannotConnectError, InvalidAuthError) as err:
        _LOGGER.warning("Album request failed: %s", err)
        connection.send_result(
            msg["id"],
            {
                "success": False,
                "error_code": "service_unavailable",
                "message": str(err),
            },
        )


# ---------------------------------------------------------------------------
# Queue handler
# ---------------------------------------------------------------------------


def _normalize_queue_item(item: dict[str, Any], service_type: str) -> dict[str, Any]:
    """Normalize a queue record from any arr service into a standard format."""
    size = item.get("size", 0)
    sizeleft = item.get("sizeleft", 0)
    progress = round((1 - sizeleft / size) * 100, 1) if size > 0 else 0.0

    # Extract media_id and human-readable title from nested objects.
    # The top-level "title" is the release/torrent name, not the media title.
    if service_type == SERVICE_RADARR:
        movie = item.get("movie") or {}
        media_id = movie.get("id") or item.get("movieId")
        title = movie.get("title", "") or item.get("title", "")
    elif service_type == SERVICE_SONARR:
        series = item.get("series") or {}
        media_id = item.get("seriesId") or series.get("id")
        title = series.get("title", "") or item.get("title", "")
    else:
        artist = item.get("artist") or {}
        media_id = item.get("artistId") or artist.get("id")
        title = artist.get("artistName", "") or item.get("title", "")

    return {
        "title": title,
        "service": service_type,
        "media_id": media_id,
        "progress": progress,
        "timeleft": item.get("timeleft") or "",
        "status": item.get("status", ""),
        "queue_id": item.get("id"),
    }


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_GET_QUEUE,
        vol.Optional("service"): str,
    }
)
@websocket_api.async_response
async def websocket_get_queue(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle get_queue — fetch download queue from arr services."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_result(msg["id"], {"items": []})
        return

    service_filter = msg.get("service")
    services = [service_filter] if service_filter else ARR_SERVICES

    all_items: list[dict[str, Any]] = []
    for svc in services:
        client = coordinator.get_client(svc)
        if client is None:
            continue
        try:
            records = await client.async_get_queue()
            for record in records:
                all_items.append(_normalize_queue_item(record, svc))
        except (CannotConnectError, InvalidAuthError, ServerError):
            pass  # skip unavailable services

    connection.send_result(msg["id"], {"items": all_items})


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register WebSocket commands for Requestarr."""
    websocket_api.async_register_command(hass, websocket_get_data)
    websocket_api.async_register_command(hass, websocket_search_movies)
    websocket_api.async_register_command(hass, websocket_search_tv)
    websocket_api.async_register_command(hass, websocket_search_music)
    websocket_api.async_register_command(hass, websocket_request_movie)
    websocket_api.async_register_command(hass, websocket_request_series)
    websocket_api.async_register_command(hass, websocket_request_artist)
    websocket_api.async_register_command(hass, websocket_get_series_seasons)
    websocket_api.async_register_command(hass, websocket_get_artist_albums)
    websocket_api.async_register_command(hass, websocket_request_album)
    websocket_api.async_register_command(hass, websocket_get_queue)
