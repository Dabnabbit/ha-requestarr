---
phase: 02-sensors-search
plan: 01
subsystem: api, sensors, websocket
tags: [homeassistant, sensor, websocket, radarr, sonarr, lidarr, arr-lookup]

requires:
  - phase: 01-config-flow-api-clients
    provides: ArrClient, RequestarrCoordinator, config flow, const.py constants
provides:
  - RequestarrSensor with service status state and library count attributes
  - Three WebSocket search commands (search_movies, search_tv, search_music)
  - ArrClient.async_search method for arr lookup endpoints
  - Result normalization with public CDN image URLs
affects: [03-movie-tv-request, 04-music-lidarr-request, 05-library-state-card-polish]

tech-stack:
  added: []
  patterns: [CoordinatorEntity sensor, WebSocket command handler, result normalization]

key-files:
  created: []
  modified:
    - custom_components/requestarr/sensor.py
    - custom_components/requestarr/websocket.py
    - custom_components/requestarr/api.py
    - custom_components/requestarr/const.py
    - custom_components/requestarr/coordinator.py
    - custom_components/requestarr/strings.json
    - custom_components/requestarr/translations/en.json

key-decisions:
  - "Sensor state is service status (connected/disconnected/error), not library count"
  - "WebSocket search errors use send_result with error field, not send_error, for business logic errors"
  - "Fresh coordinator lookup on each WS call prevents stale references after reconfigure"
  - "Profile name resolved from stored profiles list by matching current profile ID"

patterns-established:
  - "Conditional entity creation: only create sensors for coordinator.configured_services"
  - "Generic search handler factory: _handle_search delegates to service-specific normalize functions"
  - "Image URL pipeline: extract remotePoster -> rewrite TMDB to w300 -> pass through TheTVDB/fanart.tv"

requirements-completed: [SENS-01, SENS-02, SENS-03, SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05]

duration: ~15min
completed: 2026-02-27
---

# Phase 2: Sensors + Search Summary

**Conditional service status sensors with WebSocket search commands proxying arr lookup endpoints and normalizing results with public CDN image URLs**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Conditional sensors (one per configured service) showing connected/disconnected/error status with library count, service URL, and last sync as attributes
- Three WebSocket search commands (search_movies, search_tv, search_music) returning normalized results capped at 20
- TMDB poster URL rewriting from /original/ to /w300/ for card-sized thumbnails
- Structured error handling with distinct codes: invalid_query, service_not_configured, service_unavailable
- Search results pre-tagged with in_library, arr_id, external IDs, and default profile/folder info

## Task Commits

Each task was committed atomically:

1. **Task 1: Add lookup constants and search method** - `75318f7` (feat)
2. **Task 2: Replace template sensors with service status sensors** - `6422957` (feat)
3. **Task 3: Implement search WebSocket commands** - `53562b4` (feat)

## Files Created/Modified
- `custom_components/requestarr/const.py` - Added LOOKUP_ENDPOINTS, WS_TYPE constants, MAX_SEARCH_RESULTS
- `custom_components/requestarr/api.py` - Added async_search method to ArrClient
- `custom_components/requestarr/coordinator.py` - Added get_client, last_sync tracking, dt_util import
- `custom_components/requestarr/sensor.py` - Full rewrite: RequestarrSensor with conditional creation
- `custom_components/requestarr/websocket.py` - Full rewrite: three search commands with normalization
- `custom_components/requestarr/strings.json` - Added entity sensor name translations
- `custom_components/requestarr/translations/en.json` - Added entity sensor name translations

## Decisions Made
- Used `send_result` with error field (not `send_error`) for business logic errors so the card can parse structured error codes
- Resolved profile name from stored profiles list by matching current quality_profile_id, rather than storing the name separately
- Artists return year=None since they don't have a single release year

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- WebSocket search commands return self-contained results (title, poster, IDs, profile, folder) -- card has everything needed for search display AND one-click requests
- Phase 3 can add request_movie and request_series commands and build the card UI consuming these search results
- Phase 4 can add request_artist command for Lidarr

---
*Phase: 02-sensors-search*
*Completed: 2026-02-27*
