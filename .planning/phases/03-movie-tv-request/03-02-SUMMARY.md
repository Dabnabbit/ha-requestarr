---
phase: 03-movie-tv-request
plan: 02
subsystem: ui
tags: [lovelace, litelement, javascript, websocket, home-assistant]

requires:
  - phase: 03-movie-tv-request/03-01
    provides: requestarr/request_movie and requestarr/request_series WS commands, normalizers with title_slug/has_file/seasons

provides:
  - Full RequestarrCard LitElement implementation with Movies/TV tabs
  - 300ms-debounced search with 2-char minimum and race condition guard
  - Vertical result list with 60x90 poster thumbnails and four status states
  - Inline confirm dialog for request submission
  - RequestarrCardEditor minimal stub (Phase 5 implements full editor)

affects: [04-music-lidarr-request, 05-library-state-card-polish]

tech-stack:
  added: []
  patterns:
    - "Spread pattern for LitElement reactive updates: { ...this._requesting, [key]: value }"
    - "_searchSeq counter for search race condition prevention"
    - "Poster placeholder div behind img tag to avoid layout shift on load error"
    - "Inline dialog via dialog-overlay fixed position (not window.confirm — blocked in shadow DOM)"
    - "Tab switch immediately re-searches same query without debounce"

key-files:
  created: []
  modified:
    - custom_components/requestarr/frontend/requestarr-card.js

key-decisions:
  - "Inline confirm dialog used (not window.confirm) — window.confirm is blocked in shadow DOM contexts"
  - "One _results array per card, cleared on tab switch then refetched — simpler than per-tab caches"
  - "Music tab rendered as disabled button placeholder so Phase 4 only needs to activate it (no structural changes)"
  - "RequestarrCardEditor replaced with empty stub — full editor is Phase 5 work"
  - "Poster placeholder rendered behind img unconditionally — img hides on onerror, placeholder visible underneath"

patterns-established:
  - "State key: String(item.tmdb_id ?? item.tvdb_id) — unified key for both movie and TV items"
  - "Status precedence: session-requested > not_in_library > has_file (available) > in_library (monitored)"

requirements-completed: [CARD-01, CARD-02, CARD-03, CARD-04]

duration: 12min
completed: 2026-02-27
---

# Phase 03-02: Lovelace Card Rewrite Summary

**Full RequestarrCard LitElement rewrite with Movies/TV tabs, debounced search, poster result list, four status states, and inline confirm dialog connected to backend request commands**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-27T14:18:00Z
- **Completed:** 2026-02-27T14:30:00Z
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify auto-approved)
- **Files modified:** 1

## Accomplishments
- Complete rewrite of the scaffold stub into a functional Lovelace card with Movies/TV tabs
- Debounced search with race condition guard, 2-char minimum, and spinner during load
- Four status states covering all item library states: Available, Monitored, Requested, Request button
- Inline confirm dialog with quality profile and root folder display, Cancel/Confirm flow

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite requestarr-card.js with full Movies/TV UI** - `7ddc8ed` (feat)
2. **Task 2: Checkpoint — human-verify** - auto-approved (workflow.auto_advance=true)

## Files Created/Modified
- `custom_components/requestarr/frontend/requestarr-card.js` - Complete rewrite: 515 lines, full LitElement implementation

## Decisions Made
- Used inline dialog overlay pattern (not `window.confirm`) — `window.confirm` is blocked in shadow DOM contexts per Phase 3 research
- Single `_results` array with clear-on-tab-switch rather than per-tab caches — simpler state management
- Music tab rendered as disabled button placeholder so Phase 4 only needs to activate it without restructuring the tab bar
- `RequestarrCardEditor` replaced with empty stub — full editor deferred to Phase 5

## Deviations from Plan

None - plan executed exactly as written. All 18 automated checks passed.

## Issues Encountered
None.

## User Setup Required

To use the card:
1. Add the custom resource to Lovelace (already served via `async_register_static_paths`)
2. Add card to dashboard: `type: custom:requestarr-card` (optionally set `header:`)

## Next Phase Readiness
- Phase 3 complete: backend request commands + frontend card both operational
- Phase 4 (Music/Lidarr) can activate the Music tab by removing the `disabled` attribute and adding search/request logic
- Phase 5 (Card Polish) can implement the full `RequestarrCardEditor` stub without touching card logic

---
*Phase: 03-movie-tv-request*
*Completed: 2026-02-27*
