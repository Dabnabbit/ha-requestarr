"""API client for Requestarr — uniform client for Radarr, Sonarr, and Lidarr."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    API_VERSIONS,
    DEFAULT_TIMEOUT,
    LIBRARY_ENDPOINTS,
    LOOKUP_ENDPOINTS,
    QUEUE_PAGE_SIZE,
)

_LOGGER = logging.getLogger(__name__)


class CannotConnectError(Exception):
    """Raised when a connection or timeout error occurs."""


class InvalidAuthError(Exception):
    """Raised when the API returns a 401 or 403 response."""


class ServerError(Exception):
    """Raised when the server returns a non-auth HTTP error (4xx/5xx)."""


class ArrClient:
    """Uniform API client for Radarr, Sonarr, and Lidarr.

    Handles API version differences automatically:
    - Radarr: /api/v3/
    - Sonarr: /api/v3/
    - Lidarr: /api/v1/

    All services use X-Api-Key header authentication.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        service_type: str,
        session: aiohttp.ClientSession,
        verify_ssl: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the arr API client.

        Args:
            base_url: User-entered base URL (e.g., http://192.168.1.50:7878).
            api_key: API key for the arr service.
            service_type: One of 'radarr', 'sonarr', 'lidarr'.
            session: Shared aiohttp session from HA.
            verify_ssl: Whether to verify SSL certificates.
            timeout: Request timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._service_type = service_type
        self._api_version = API_VERSIONS[service_type]
        self._session = session
        self._ssl: bool | None = None if verify_ssl else False
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def _api_base(self) -> str:
        """Return the API base URL including version prefix."""
        return f"{self._base_url}/api/{self._api_version}"

    def _headers(self) -> dict[str, str]:
        """Return authentication headers."""
        return {"X-Api-Key": self._api_key}

    async def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Any:
        """Make an authenticated request to the arr API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path (e.g., /system/status).
            **kwargs: Additional arguments passed to aiohttp.

        Returns:
            Parsed JSON response, or empty dict if response body is empty.

        Raises:
            CannotConnectError: On connection/timeout errors.
            InvalidAuthError: On 401/403 responses.
            ServerError: On other 4xx/5xx responses.
        """
        url = f"{self._api_base}{endpoint}"
        try:
            response = await self._session.request(
                method,
                url,
                headers=self._headers(),
                ssl=self._ssl,
                timeout=self._timeout,
                **kwargs,
            )
        except aiohttp.ClientConnectionError as err:
            raise CannotConnectError(
                f"Connection error to {self._service_type}: {err}"
            ) from err
        except aiohttp.ClientError as err:
            raise CannotConnectError(
                f"Client error for {self._service_type}: {err}"
            ) from err
        except asyncio.TimeoutError as err:
            raise CannotConnectError(
                f"Request to {self._service_type} timed out"
            ) from err

        if response.status in (401, 403):
            raise InvalidAuthError(
                f"Authentication failed for {self._service_type} "
                f"(HTTP {response.status})"
            )

        if response.status >= 400:
            try:
                body = await response.text()
            except Exception:
                body = ""
            raise ServerError(
                f"{self._service_type} returned HTTP {response.status}: "
                f"{response.reason}. {body}"
            )

        # Handle empty response bodies (some endpoints return 200 with no body)
        text = await response.text()
        if not text or not text.strip():
            return {}

        return await response.json(content_type=None)

    async def async_validate_connection(self) -> bool:
        """Validate the connection via /system/status.

        Returns:
            True if connection is valid.

        Raises:
            CannotConnectError: Cannot reach the service.
            InvalidAuthError: API key is invalid.
        """
        await self._request("GET", "/system/status")
        return True

    async def async_get_quality_profiles(self) -> list[dict[str, Any]]:
        """Fetch quality profiles from the arr service.

        Returns:
            List of quality profile dicts with at least 'id' and 'name'.
        """
        return await self._request("GET", "/qualityprofile")

    async def async_get_root_folders(self) -> list[dict[str, Any]]:
        """Fetch root folders from the arr service.

        Returns:
            List of root folder dicts with at least 'id' and 'path'.
        """
        return await self._request("GET", "/rootfolder")

    async def async_get_metadata_profiles(self) -> list[dict[str, Any]]:
        """Fetch metadata profiles from Lidarr.

        Only applicable to Lidarr. Radarr and Sonarr do not have
        metadata profiles.

        Returns:
            List of metadata profile dicts with at least 'id' and 'name'.
        """
        return await self._request("GET", "/metadataprofile")

    async def async_search(self, query: str) -> list[dict[str, Any]]:
        """Search the arr service's lookup endpoint.

        Args:
            query: Search term.

        Returns:
            List of raw result dicts from the arr API.
        """
        endpoint = LOOKUP_ENDPOINTS[self._service_type]
        return await self._request("GET", endpoint, params={"term": query})

    async def async_request_movie(
        self,
        tmdb_id: int,
        title: str,
        title_slug: str,
        quality_profile_id: int,
        root_folder_path: str,
    ) -> dict[str, Any]:
        """Add a movie to Radarr.

        Args:
            tmdb_id: TMDB ID of the movie.
            title: Movie title.
            title_slug: URL-friendly slug (e.g. "interstellar-157336").
            quality_profile_id: Quality profile ID from config entry.
            root_folder_path: Root folder path from config entry.

        Returns:
            Parsed JSON response from Radarr.

        Raises:
            CannotConnectError: Cannot reach Radarr.
            InvalidAuthError: API key rejected.
            ServerError: Non-auth HTTP error. HTTP 400 means movie already exists.
        """
        payload = {
            "tmdbId": tmdb_id,
            "title": title,
            "titleSlug": title_slug,
            "qualityProfileId": int(quality_profile_id),
            "rootFolderPath": root_folder_path,
            "monitored": True,
            "minimumAvailability": "released",
            "addOptions": {"searchForMovie": True},
        }
        return await self._request("POST", "/movie", json=payload)

    async def async_request_series(
        self,
        tvdb_id: int,
        title: str,
        title_slug: str,
        quality_profile_id: int,
        root_folder_path: str,
        seasons: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Add a series to Sonarr.

        Args:
            tvdb_id: TVDB ID of the series.
            title: Series title.
            title_slug: URL-friendly slug.
            quality_profile_id: Quality profile ID from config entry.
            root_folder_path: Root folder path from config entry.
            seasons: Raw seasons list from Sonarr lookup response.

        Returns:
            Parsed JSON response from Sonarr.

        Raises:
            CannotConnectError: Cannot reach Sonarr.
            InvalidAuthError: API key rejected.
            ServerError: Non-auth HTTP error. HTTP 400 means series already exists.
        """
        all_monitored = all(s.get("monitored", True) for s in seasons)
        payload = {
            "tvdbId": tvdb_id,
            "title": title,
            "titleSlug": title_slug,
            "qualityProfileId": int(quality_profile_id),
            "rootFolderPath": root_folder_path,
            "monitored": True,
            "seasonFolder": True,
            "seriesType": "standard",
            "seasons": [
                {"seasonNumber": s.get("seasonNumber", 0), "monitored": s.get("monitored", True)}
                for s in seasons
            ],
            "addOptions": {
                "searchForMissingEpisodes": True,
                "monitor": "all" if all_monitored else "none",
            },
        }
        return await self._request("POST", "/series", json=payload)

    async def async_request_artist(
        self,
        foreign_artist_id: str,
        artist_name: str,
        quality_profile_id: int,
        metadata_profile_id: int,
        root_folder_path: str,
    ) -> dict[str, Any]:
        """Add an artist to Lidarr.

        Args:
            foreign_artist_id: MusicBrainz artist GUID (string UUID).
            artist_name: Display name for the artist (required by Lidarr).
            quality_profile_id: Quality profile ID from config entry.
            metadata_profile_id: Metadata profile ID from config entry (Lidarr-specific).
            root_folder_path: Root folder path from config entry.

        Returns:
            Parsed JSON response from Lidarr.

        Raises:
            CannotConnectError: Cannot reach Lidarr.
            InvalidAuthError: API key rejected.
            ServerError: Non-auth HTTP error. HTTP 400 means artist already exists.
        """
        payload = {
            "foreignArtistId": foreign_artist_id,        # string UUID — DO NOT cast to int
            "artistName": artist_name,
            "qualityProfileId": int(quality_profile_id),
            "metadataProfileId": int(metadata_profile_id),
            "rootFolderPath": root_folder_path,
            "monitored": True,
            "addOptions": {
                "searchForMissingAlbums": True,
                "monitor": "all",
            },
        }
        return await self._request("POST", "/artist", json=payload)

    async def async_monitor_seasons(
        self, arr_id: int, season_numbers: list[int]
    ) -> dict[str, Any]:
        """Monitor and search specific seasons for an existing Sonarr series.

        Fetches the current series data, sets the requested seasons to
        monitored=True, saves via PUT, then triggers a SeasonSearch for each
        newly monitored season.

        Args:
            arr_id: Sonarr internal series ID.
            season_numbers: Season numbers to monitor and search.

        Returns:
            Updated series dict from Sonarr.
        """
        series = await self._request("GET", f"/series/{arr_id}")
        for s in series.get("seasons", []):
            if s.get("seasonNumber") in season_numbers:
                s["monitored"] = True
        series["monitored"] = True
        result = await self._request("PUT", f"/series/{arr_id}", json=series)

        for sn in season_numbers:
            try:
                await self._request(
                    "POST",
                    "/command",
                    json={"name": "SeasonSearch", "seriesId": arr_id, "seasonNumber": sn},
                )
            except ServerError:
                pass  # search command failure is non-critical
        return result

    async def async_get_series_seasons(self, arr_id: int) -> list[dict[str, Any]]:
        """Fetch accurate season data for an in-library series from Sonarr.

        The lookup endpoint (/series/lookup) does not reliably include season
        statistics such as episodeFileCount. This method calls /series/{arr_id}
        directly to get the full library entry with accurate per-season stats.

        Args:
            arr_id: Sonarr internal series ID (from lookup result id field).

        Returns:
            List of season dicts including statistics.episodeFileCount.
        """
        result = await self._request("GET", f"/series/{arr_id}")
        if isinstance(result, dict):
            return result.get("seasons", [])
        return []

    async def async_get_artist_albums(
        self, foreign_artist_id: str, arr_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch albums for an artist from Lidarr.

        Args:
            foreign_artist_id: MusicBrainz artist GUID.
            arr_id: Lidarr internal artist ID if artist is already in library.
                    When set, uses /album endpoint (returns actual library state).
                    When None, uses /album/lookup (returns all known albums, id=0).

        Returns:
            List of album dicts with title, year, foreign_album_id, monitored, in_library.
        """
        from_library = bool(arr_id)
        if from_library:
            items = await self._request("GET", "/album", params={"artistId": arr_id})
        else:
            items = await self._request(
                "GET", "/album/lookup", params={"term": f"lidarr:{foreign_artist_id}"}
            )
        result = []
        for item in items if isinstance(items, list) else []:
            fid = item.get("foreignAlbumId") or item.get("foreignId")
            if not fid:
                continue
            stats = item.get("statistics") or {}
            track_file_count = stats.get("trackFileCount", 0)
            total_track_count = stats.get("totalTrackCount", 0)
            # Library endpoint: album has actual downloaded tracks
            # Lookup endpoint: id > 0 means it's tracked in library
            in_library = track_file_count > 0 if from_library else item.get("id", 0) > 0
            result.append({
                "title": item.get("title", ""),
                "year": item.get("releaseDate", "")[:4] if item.get("releaseDate") else None,
                "foreign_album_id": fid,
                "monitored": item.get("monitored", False),
                "in_library": in_library,
                "track_file_count": track_file_count,
                "total_track_count": total_track_count,
            })
        return result

    async def async_request_album(
        self,
        foreign_artist_id: str,
        foreign_album_id: str,
        artist_name: str,
        quality_profile_id: int,
        metadata_profile_id: int,
        root_folder_path: str,
    ) -> dict[str, Any]:
        """Add an artist to Lidarr with only the target album monitored.

        Fetches the full album list via lookup, sets the target album to
        monitored=True and all others to False, then POSTs the artist with
        addOptions.monitor="none" so Lidarr respects the per-album flags.

        Args:
            foreign_artist_id: MusicBrainz artist GUID.
            foreign_album_id: MusicBrainz album GUID.
            artist_name: Display name for the artist (required by Lidarr).
            quality_profile_id: Quality profile ID from config entry.
            metadata_profile_id: Metadata profile ID from config entry.
            root_folder_path: Root folder path from config entry.

        Returns:
            Parsed JSON response from Lidarr.

        Raises:
            CannotConnectError: Cannot reach Lidarr.
            InvalidAuthError: API key rejected.
            ServerError: Non-auth HTTP error. HTTP 400 means artist already exists.
        """
        all_albums = await self._request(
            "GET", "/album/lookup", params={"term": f"lidarr:{foreign_artist_id}"}
        )
        album_list = [
            {
                "foreignAlbumId": a.get("foreignAlbumId") or a.get("foreignId"),
                "monitored": (a.get("foreignAlbumId") or a.get("foreignId")) == foreign_album_id,
            }
            for a in (all_albums if isinstance(all_albums, list) else [])
            if a.get("foreignAlbumId") or a.get("foreignId")
        ]
        payload = {
            "foreignArtistId": foreign_artist_id,
            "artistName": artist_name,
            "qualityProfileId": int(quality_profile_id),
            "metadataProfileId": int(metadata_profile_id),
            "rootFolderPath": root_folder_path,
            "monitored": True,
            "addOptions": {"monitor": "none", "searchForMissingAlbums": True},
            "albums": album_list,
        }
        return await self._request("POST", "/artist", json=payload)

    async def async_get_queue(self) -> list[dict[str, Any]]:
        """Fetch the download queue from the arr service.

        Includes nested media objects (movie/series/artist) for readable titles.

        Returns:
            List of queue record dicts from the arr API.
        """
        # Each service needs its own include params for nested media objects
        include_params = {
            "radarr": {"includeMovie": "true"},
            "sonarr": {"includeSeries": "true"},
            "lidarr": {"includeArtist": "true", "includeAlbum": "true"},
        }
        params = {"pageSize": QUEUE_PAGE_SIZE}
        params.update(include_params.get(self._service_type, {}))
        data = await self._request("GET", "/queue", params=params)
        if isinstance(data, dict):
            return data.get("records", [])
        return []

    async def async_get_library_count(self) -> int:
        """Fetch the total number of items in the library.

        Uses the service-specific library endpoint:
        - Radarr: /movie (returns all movies)
        - Sonarr: /series (returns all series)
        - Lidarr: /artist (returns all artists)

        Returns:
            Total count of library items.
        """
        endpoint = LIBRARY_ENDPOINTS[self._service_type]
        items = await self._request("GET", endpoint)
        if isinstance(items, list):
            return len(items)
        return 0
