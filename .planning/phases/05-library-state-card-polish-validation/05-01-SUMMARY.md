---
phase: 05-library-state-card-polish-validation
plan: "01"
subsystem: ui
tags: [lovelace, lit-element, javascript, home-assistant]

requires:
  - phase: 04-music-lidarr-request
    provides: Music tab with circular avatars and in_library field in all search results

provides:
  - Green .badge-in-library pill overlay on poster/avatar for in-library items
  - Disabled "In Library" button replacing Request button for in-library items
  - Simplified 3-state _getItemState (requested, in_library, not_in_library)
  - Full RequestarrCardEditor with service toggles and title field
affects: [05-library-state-card-polish-validation]

tech-stack:
  added: []
  patterns:
    - "Key passed as parameter to _renderStatus — no internal key recomputation"
    - "In-library badge uses absolute positioning within poster-wrap/avatar-wrap (already position:relative + overflow:hidden)"

key-files:
  created: []
  modified:
    - custom_components/requestarr/frontend/requestarr-card.js

key-decisions:
  - "Removed available/monitored states entirely — in_library is the single consolidated state for items in the arr library"
  - "badge-in-library uses absolute positioning at bottom of poster/avatar — no height changes to container needed"
  - "RequestarrCardEditor detects services via startsWith prefix match on hass.states keys (handles HA numeric suffixes)"

requirements-completed:
  - REQT-05
  - CARD-05

duration: 8min
completed: 2026-02-28
---

# Phase 05 Plan 01: In-Library Badges and Card Editor Summary

**Green in-library pill badge on poster/avatar thumbnails, disabled "In Library" button for owned items, and full RequestarrCardEditor with service toggles and title field — all in requestarr-card.js**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-28T02:20:00Z
- **Completed:** 2026-02-28T02:28:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Simplified _getItemState from 4 states to 3 — removed available/monitored, added in_library
- Fixed _renderStatus signature to (state, key, item) — key parameter eliminates internal recomputation bug for music items
- Added green .badge-in-library pill overlay inside poster-wrap and avatar-wrap using absolute positioning
- Disabled .req-btn-in-library button (gray) replaces Request button for in-library items
- Replaced RequestarrCardEditor stub with full implementation: title input, per-service checkboxes (only configured services), config-changed event dispatch
- Bumped CARD_VERSION to 0.5.0

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix _getItemState, _renderStatus, add badge** - `8add733` (feat)
2. **Task 2: Implement RequestarrCardEditor** - `b32fa05` (feat)

## Files Created/Modified
- `custom_components/requestarr/frontend/requestarr-card.js` - In-library state model, badge overlay, full card editor

## Decisions Made
- Removed `available` and `monitored` states since `in_library` (`id > 0`) is sufficient for the UX goal — users don't need to distinguish monitored vs downloaded in this card
- Used `startsWith` prefix match for service detection in editor (handles `sensor.requestarr_radarr_2` HA-generated suffixes)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 05-01 complete; plan 05-02 (test suite rewrite + README) can proceed independently
- Both plans are in Wave 1 and have no dependencies on each other

---
*Phase: 05-library-state-card-polish-validation*
*Completed: 2026-02-28*
