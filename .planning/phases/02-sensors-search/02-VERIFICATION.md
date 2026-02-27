---
phase: 02-sensors-search
status: passed
verified: 2026-02-27
---

# Phase 2: Sensors + Search - Verification

## Phase Goal
Library count sensors visible in HA; WebSocket search commands return arr lookup results with public CDN image URLs

## Success Criteria Verification

### SC-1: Library count sensors show correct values (only for configured services)
**Status: PASSED**
- Sensors only created for `coordinator.configured_services` (conditional creation in `async_setup_entry`)
- Library count exposed as `extra_state_attributes["library_count"]`
- Sensor state is service health: connected/disconnected/error
- One sensor per configured service with MDI icons (mdi:movie, mdi:television, mdi:music)

### SC-2: Movie search returns Radarr lookup results with TMDB CDN poster URLs
**Status: PASSED**
- `websocket_search_movies` command registered, delegates to `_handle_search` with `SERVICE_RADARR`
- TMDB URLs rewritten from `/t/p/original/` to `/t/p/w300/` via `_rewrite_tmdb_poster()`
- Results include `tmdb_id` for downstream request flow

### SC-3: TV search returns Sonarr lookup results with TheTVDB CDN poster URLs
**Status: PASSED**
- `websocket_search_tv` command registered, delegates to `_handle_search` with `SERVICE_SONARR`
- TheTVDB URLs passed through unchanged (no rewriting applied)
- Results include `tvdb_id` for downstream request flow

### SC-4: Music search returns Lidarr lookup results with fanart.tv CDN image URLs
**Status: PASSED**
- `websocket_search_music` command registered, delegates to `_handle_search` with `SERVICE_LIDARR`
- fanart.tv URLs passed through unchanged (no rewriting applied)
- Results include `foreign_artist_id` for downstream request flow
- Uses `artistName` field (Lidarr-specific) for title

### SC-5: Arr API keys never exposed to card/browser
**Status: PASSED**
- Normalization functions extract `remotePoster`/`remoteUrl` fields (public CDN URLs)
- No `MediaCoverProxy` URLs in any response (these require API key auth)
- No `api_key` or arr service base URLs in normalized result payloads
- Only public CDN domains in poster_url: image.tmdb.org, artworks.thetvdb.com, assets.fanart.tv

## Requirement Coverage

| ID | Description | Status | Evidence |
|----|-------------|--------|----------|
| SENS-01 | Radarr movie count sensor | PASSED | sensor.py creates Radarr sensor with library_count attribute |
| SENS-02 | Sonarr series count sensor | PASSED | sensor.py creates Sonarr sensor with library_count attribute |
| SENS-03 | Lidarr artist count sensor | PASSED | sensor.py creates Lidarr sensor with library_count attribute |
| SRCH-01 | Movie search via Radarr lookup | PASSED | websocket.py search_movies -> /movie/lookup via ArrClient.async_search |
| SRCH-02 | TV search via Sonarr lookup | PASSED | websocket.py search_tv -> /series/lookup via ArrClient.async_search |
| SRCH-03 | Music search via Lidarr lookup | PASSED | websocket.py search_music -> /artist/lookup via ArrClient.async_search |
| SRCH-04 | Results display poster, title, year, description | PASSED | All normalize functions include poster_url, title, year, overview |
| SRCH-05 | API keys stay server-side | PASSED | Only public CDN URLs in responses, no MediaCoverProxy, no api_key |

## Must-Haves Verification

| Truth | Status |
|-------|--------|
| Each configured arr service has a sensor showing connected/disconnected/error | PASSED |
| Movie search returns Radarr lookup results with TMDB CDN poster URLs (w300) | PASSED |
| TV search returns Sonarr lookup results with TheTVDB CDN poster URLs | PASSED |
| Music search returns Lidarr lookup results with fanart.tv CDN image URLs | PASSED |
| Arr API keys never appear in any WebSocket response payload | PASSED |
| Search results include in_library, arr_id, external IDs, and default profile/folder | PASSED |
| Unconfigured services return service_not_configured error, not crash | PASSED |

## Key Artifacts

| Artifact | Status |
|----------|--------|
| sensor.py with RequestarrSensor | Present, uses CoordinatorEntity[RequestarrCoordinator] |
| websocket.py with 3 search commands | Present, search_movies/search_tv/search_music registered |
| api.py with async_search | Present, uses LOOKUP_ENDPOINTS per service type |
| const.py with LOOKUP_ENDPOINTS + WS types | Present, all constants defined |

## Key Links

| Link | Status |
|------|--------|
| sensor.py imports RequestarrCoordinator (not TemplateCoordinator) | VERIFIED |
| websocket.py looks up config entry fresh on each call | VERIFIED |
| api.py async_search uses LOOKUP_ENDPOINTS keyed by service_type | VERIFIED |
| Image URLs use remoteUrl/remotePoster (public CDN) | VERIFIED |

## Overall Result

**Status: PASSED**
**Score: 8/8 requirements verified, 5/5 success criteria met**

---
*Phase: 02-sensors-search*
*Verified: 2026-02-27*
