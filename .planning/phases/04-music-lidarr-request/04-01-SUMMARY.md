---
phase: 04-music-lidarr-request
plan: 01
subsystem: api, ui
tags: [lidarr, websocket, litelement, circular-avatar, music-request]

requires:
  - phase: 03-movie-tv-request
    provides: websocket request pattern (send_result/send_error), LitElement card with tabs, confirm dialog, four-state badge system
  - phase: 02-sensors-search
    provides: websocket_search_music command, _normalize_music_result, ArrClient.async_search for Lidarr

provides:
  - requestarr/request_artist WebSocket command (Lidarr POST /api/v1/artist)
  - ArrClient.async_request_artist method (foreignArtistId + metadataProfileId)
  - _normalize_music_result extended with metadata_profile field
  - Active Music tab in Lovelace card with circular avatar rows
  - Deterministic initials placeholder with 10-color hash palette
  - Metadata profile name shown in confirm dialog for music requests

affects: [05-library-state-card-polish]

tech-stack:
  added: []
  patterns:
    - foreignArtistId is a string UUID (not int) — special case vs tmdbId/tvdbId
    - metadataProfileId is Lidarr-specific; must be included in POST alongside qualityProfileId
    - Circular avatar: border-radius 50% on fixed-size container with overflow hidden
    - Initials placeholder: always rendered behind img; @error hides img to reveal placeholder
    - Deterministic color: djb2 hash of artist name mod palette length

key-files:
  created: []
  modified:
    - custom_components/requestarr/const.py
    - custom_components/requestarr/api.py
    - custom_components/requestarr/websocket.py
    - custom_components/requestarr/frontend/requestarr-card.js

key-decisions:
  - "foreignArtistId is a string UUID — not cast to int (unlike tmdbId/tvdbId)"
  - "metadataProfileId required by Lidarr; read from CONF_LIDARR_METADATA_PROFILE_ID"
  - "Music result key uses foreign_artist_id; movie/TV key uses tmdb_id ?? tvdb_id"
  - "Lidarr lookup stats not reliable — all in-library artists show Monitored (same as Sonarr TV)"
  - "Avatar diameter 60px matches poster row height; music rows use align-items: center"
  - "checkpoint:human-verify auto-approved (workflow.auto_advance: true)"

patterns-established:
  - "Music item key: String(item.foreign_artist_id) — separate from movies/TV"
  - "Circular avatar: .avatar-wrap (60x60, border-radius: 50%) + .avatar (img) + .avatar-placeholder (always visible)"
  - "_hashColor(name): djb2 hash → 10-color palette for deterministic initials colors"

requirements-completed: [SRCH-03, REQT-03]

duration: 25min
completed: 2026-02-27
---

# Phase 4: Music + Lidarr Request Summary

**Lidarr artist request command + Music tab with circular avatars and deterministic initials placeholder**

## Performance

- **Duration:** 25 min
- **Started:** 2026-02-27T00:00:00Z
- **Completed:** 2026-02-27T00:25:00Z
- **Tasks:** 4 auto + 1 checkpoint (auto-approved)
- **Files modified:** 4

## Accomplishments
- Added `requestarr/request_artist` WebSocket command — POSTs to Lidarr `/api/v1/artist` with foreignArtistId (string UUID), qualityProfileId, metadataProfileId, rootFolderPath
- Extended `_normalize_music_result` with `metadata_profile` field so confirm dialog shows Metadata profile name
- Activated Music tab: full search via `requestarr/search_music` + request via `requestarr/request_artist`
- Circular 60px avatar rows with fanart.tv images and deterministic initials placeholder (djb2 hash → 10-color palette)
- Dialog extended to show Metadata profile line for music requests

## Task Commits

1. **Task 1: Add WS_TYPE_REQUEST_ARTIST constant** - `663630c` (feat)
2. **Task 2: Add async_request_artist to ArrClient** - `b41791b` (feat)
3. **Task 3: Extend normalizer + add request handler + register** - `75deec7` (feat)
4. **Task 4: Activate Music tab with circular avatar rows** - `b4b8298` (feat)

## Files Created/Modified
- `custom_components/requestarr/const.py` - Added WS_TYPE_REQUEST_ARTIST constant
- `custom_components/requestarr/api.py` - Added async_request_artist (POST /artist with foreignArtistId + metadataProfileId)
- `custom_components/requestarr/websocket.py` - Extended normalizer + added websocket_request_artist + registration
- `custom_components/requestarr/frontend/requestarr-card.js` - Activated Music tab, circular avatar rows, _hashColor, _renderMusicResultRow, extended dialog

## Decisions Made
- `foreignArtistId` kept as string (MusicBrainz UUID) — no int cast, unlike tmdbId/tvdbId
- `metadataProfileId` required for all Lidarr artist POST requests
- Music item key uses `foreign_artist_id` (not tmdb_id/tvdb_id) in `_requesting` and `_requestError` maps
- All in-library artists show "Monitored" (blue) — same pattern as Sonarr TV, lookup stats unreliable
- `checkpoint:human-verify` auto-approved (workflow.auto_advance: true in config)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Phase 4 complete. Phase 5 (Library State + Card Polish + Validation) is now unblocked.
- Phase 5 will add persistent library state badges and visual card editor.

---
*Phase: 04-music-lidarr-request*
*Completed: 2026-02-27*
