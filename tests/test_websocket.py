"""Tests for Requestarr WebSocket handlers."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.requestarr.api import ArrClient, CannotConnectError, ServerError


async def test_search_movies_in_library(
    hass: HomeAssistant, hass_ws_client, radarr_entry
) -> None:
    """Search result with id > 0 has in_library=True and TMDB URL rewritten to w300."""
    raw = [
        {
            "id": 42,
            "title": "Inception",
            "year": 2010,
            "tmdbId": 27205,
            "titleSlug": "inception",
            "hasFile": True,
            "remotePoster": "https://image.tmdb.org/t/p/original/test.jpg",
        }
    ]
    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=1
    ):
        with patch.object(
            ArrClient, "async_search", new_callable=AsyncMock, return_value=raw
        ):
            radarr_entry.add_to_hass(hass)
            assert await hass.config_entries.async_setup(radarr_entry.entry_id)
            await hass.async_block_till_done()
            client = await hass_ws_client(hass)
            await client.send_json(
                {"id": 1, "type": "requestarr/search_movies", "query": "inception"}
            )
            result = await client.receive_json()

    assert result["success"] is True
    item = result["result"]["results"][0]
    assert item["in_library"] is True
    assert item["arr_id"] == 42
    assert item["poster_url"] == "https://image.tmdb.org/t/p/w300/test.jpg"


async def test_search_movies_not_in_library(
    hass: HomeAssistant, hass_ws_client, radarr_entry
) -> None:
    """Search result with id == 0 has in_library=False."""
    raw = [
        {
            "id": 0,
            "title": "Dune Part Two",
            "year": 2024,
            "tmdbId": 693134,
            "titleSlug": "dune-part-two",
            "hasFile": False,
            "remotePoster": "https://image.tmdb.org/t/p/original/poster.jpg",
        }
    ]
    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=0
    ):
        with patch.object(
            ArrClient, "async_search", new_callable=AsyncMock, return_value=raw
        ):
            radarr_entry.add_to_hass(hass)
            assert await hass.config_entries.async_setup(radarr_entry.entry_id)
            await hass.async_block_till_done()
            client = await hass_ws_client(hass)
            await client.send_json(
                {"id": 1, "type": "requestarr/search_movies", "query": "dune"}
            )
            result = await client.receive_json()

    assert result["success"] is True
    item = result["result"]["results"][0]
    assert item["in_library"] is False
    assert item["arr_id"] is None


async def test_search_music_in_library(
    hass: HomeAssistant, hass_ws_client, lidarr_entry
) -> None:
    """Lidarr artist search result with id > 0 has in_library=True."""
    raw = [
        {
            "id": 7,
            "artistName": "Radiohead",
            "overview": "British rock band",
            "foreignArtistId": "a74b1b7f-71a5-4011-9441-d0b5e4122711",
        }
    ]
    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=1
    ):
        with patch.object(
            ArrClient, "async_search", new_callable=AsyncMock, return_value=raw
        ):
            lidarr_entry.add_to_hass(hass)
            assert await hass.config_entries.async_setup(lidarr_entry.entry_id)
            await hass.async_block_till_done()
            client = await hass_ws_client(hass)
            await client.send_json(
                {"id": 1, "type": "requestarr/search_music", "query": "radiohead"}
            )
            result = await client.receive_json()

    assert result["success"] is True
    item = result["result"]["results"][0]
    assert item["in_library"] is True
    assert item["title"] == "Radiohead"


async def test_search_empty_query_rejected(
    hass: HomeAssistant, hass_ws_client, radarr_entry
) -> None:
    """Empty query returns error with invalid_query code."""
    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=5
    ):
        radarr_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(radarr_entry.entry_id)
        await hass.async_block_till_done()
        client = await hass_ws_client(hass)
        await client.send_json(
            {"id": 1, "type": "requestarr/search_movies", "query": "   "}
        )
        result = await client.receive_json()

    assert result["success"] is True  # send_result not send_error
    assert result["result"]["error"] == "invalid_query"
    assert result["result"]["results"] == []


async def test_request_movie_success(
    hass: HomeAssistant, hass_ws_client, radarr_entry
) -> None:
    """Successful movie request returns success=True."""
    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=5
    ):
        with patch.object(
            ArrClient, "async_request_movie", new_callable=AsyncMock, return_value=None
        ):
            radarr_entry.add_to_hass(hass)
            assert await hass.config_entries.async_setup(radarr_entry.entry_id)
            await hass.async_block_till_done()
            client = await hass_ws_client(hass)
            await client.send_json(
                {
                    "id": 1,
                    "type": "requestarr/request_movie",
                    "tmdb_id": 27205,
                    "title": "Inception",
                    "title_slug": "inception",
                }
            )
            result = await client.receive_json()

    assert result["success"] is True
    assert result["result"]["success"] is True


async def test_request_movie_already_exists(
    hass: HomeAssistant, hass_ws_client, radarr_entry
) -> None:
    """Movie already in Radarr (HTTP 400) returns already_exists error code."""
    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=5
    ):
        with patch.object(
            ArrClient,
            "async_request_movie",
            new_callable=AsyncMock,
            side_effect=ServerError("HTTP 400: Movie already exists"),
        ):
            radarr_entry.add_to_hass(hass)
            assert await hass.config_entries.async_setup(radarr_entry.entry_id)
            await hass.async_block_till_done()
            client = await hass_ws_client(hass)
            await client.send_json(
                {
                    "id": 1,
                    "type": "requestarr/request_movie",
                    "tmdb_id": 27205,
                    "title": "Inception",
                    "title_slug": "inception",
                }
            )
            result = await client.receive_json()

    assert result["success"] is True  # send_result, not send_error
    assert result["result"]["success"] is False
    assert result["result"]["error_code"] == "already_exists"


async def test_request_artist_success(
    hass: HomeAssistant, hass_ws_client, lidarr_entry
) -> None:
    """Successful artist request to Lidarr returns success=True."""
    with patch.object(
        ArrClient, "async_get_library_count", new_callable=AsyncMock, return_value=3
    ):
        with patch.object(
            ArrClient, "async_request_artist", new_callable=AsyncMock, return_value=None
        ):
            lidarr_entry.add_to_hass(hass)
            assert await hass.config_entries.async_setup(lidarr_entry.entry_id)
            await hass.async_block_till_done()
            client = await hass_ws_client(hass)
            await client.send_json(
                {
                    "id": 1,
                    "type": "requestarr/request_artist",
                    "foreign_artist_id": "a74b1b7f-71a5-4011-9441-d0b5e4122711",
                    "title": "Radiohead",
                }
            )
            result = await client.receive_json()

    assert result["success"] is True
    assert result["result"]["success"] is True
