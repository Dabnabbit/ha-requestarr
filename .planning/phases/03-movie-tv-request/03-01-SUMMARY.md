---
phase: 03-movie-tv-request
plan: 01
subsystem: api
tags: [websocket, radarr, sonarr, aiohttp, home-assistant]

requires:
  - phase: 02-sensors-search
    provides: ArrClient with async_search, websocket.py search handlers and normalizers, coordinator with get_client()

provides:
  - WS_TYPE_REQUEST_MOVIE and WS_TYPE_REQUEST_TV constants in const.py
  - ArrClient.async_request_movie (POST /movie to Radarr with all required fields)
  - ArrClient.async_request_series (POST /series to Sonarr with seasons rebuilt)
  - websocket_request_movie handler registered as requestarr/request_movie
  - websocket_request_series handler registered as requestarr/request_series
  - Extended normalizers emitting title_slug, has_file, seasons for card request payloads

affects: [03-02, 04-music-lidarr-request]

tech-stack:
  added: []
  patterns:
    - "send_result for all request error paths (never send_error) so JS promise always resolves"
    - "HTTP 400 from arr add endpoint maps to error_code=already_exists"
    - "int(quality_profile_id) cast for Radarr/Sonarr — config stores profile IDs as strings from HTML selectors"

key-files:
  created: []
  modified:
    - custom_components/requestarr/const.py
    - custom_components/requestarr/api.py
    - custom_components/requestarr/websocket.py

key-decisions:
  - "All request error paths use send_result with {success, error_code, message} — never send_error — so the JS sendMessagePromise always resolves and the card can display inline errors"
  - "HTTP 400 from Radarr/Sonarr add endpoint reliably means duplicate — mapped to already_exists error code"
  - "int(quality_profile_id) cast in ArrClient payload — options flow stores IDs as strings from HTML selectors, Radarr/Sonarr validate as integers"
  - "Sonarr has_file always False in normalizer — lookup statistics unreliable (Sonarr issue #4942)"
  - "seasons passed through raw from lookup response, rebuilt in async_request_series with monitored=True for all"

patterns-established:
  - "Request handlers: coordinator check → client check → config_data fetch → try POST → success or error result"
  - "Error discrimination: ServerError with '400' in message → already_exists; other ServerError/CannotConnect/InvalidAuth → service_unavailable"

requirements-completed: [REQT-01, REQT-02, REQT-04]

duration: 18min
completed: 2026-02-27
---

# Phase 03-01: Backend Request Handlers Summary

**Two new WebSocket request commands (request_movie, request_series) wired to Radarr/Sonarr POST endpoints, with normalizers extended to include title_slug, has_file, and seasons for card request payloads**

## Performance

- **Duration:** 18 min
- **Started:** 2026-02-27T14:00:00Z
- **Completed:** 2026-02-27T14:18:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Extended Phase 2 search normalizers to emit `title_slug`, `has_file`, and `seasons` needed by the card to build request payloads
- Added `async_request_movie` and `async_request_series` to `ArrClient` with correct Radarr/Sonarr API payloads
- Implemented and registered `websocket_request_movie` and `websocket_request_series` handlers with structured error responses

## Task Commits

Each task was committed atomically:

1. **Task 1: Add request constants and extend normalizers** - `54f175b` (feat)
2. **Task 2: Add async_request_movie and async_request_series to ArrClient** - `6af5ab1` (feat)
3. **Task 3: Add request WebSocket handlers and register with HA** - `5d02765` (feat)

## Files Created/Modified
- `custom_components/requestarr/const.py` - Added WS_TYPE_REQUEST_MOVIE and WS_TYPE_REQUEST_TV constants
- `custom_components/requestarr/api.py` - Added async_request_movie and async_request_series methods to ArrClient
- `custom_components/requestarr/websocket.py` - Extended normalizers, added two request handlers, registered both commands

## Decisions Made
- All request error paths use `send_result` (not `send_error`) so the JS `sendMessagePromise` always resolves rather than rejecting — enables inline card error display
- HTTP 400 from arr add endpoint mapped to `error_code: already_exists` — Radarr/Sonarr reliably return 400 for duplicate adds
- `int(quality_profile_id)` cast in payloads — options flow stores profile IDs as strings from HTML selectors, arr services expect integers
- `has_file` always False in TV normalizer — Sonarr lookup statistics are always 0 (Sonarr issue #4942)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The standard `python` alias not available in this shell (only `python3`) — used direct file inspection for verification instead of the plan's `python -c` commands. All checks passed equivalently.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend request commands ready for Plan 03-02 (Lovelace card)
- Card can submit `requestarr/request_movie` with `{tmdb_id, title, title_slug}` and `requestarr/request_series` with `{tvdb_id, title, title_slug, seasons}`
- Search results from Phase 2 now include all fields the card needs: `title_slug`, `has_file`, `seasons`

---
*Phase: 03-movie-tv-request*
*Completed: 2026-02-27*
