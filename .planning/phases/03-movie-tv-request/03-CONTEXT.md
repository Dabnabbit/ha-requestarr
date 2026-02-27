# Phase 3: Movie & TV Request - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can request movies to Radarr and TV series to Sonarr from the Lovelace card.
Scope: two WebSocket commands (request_movie, request_series) + card UI (Movies and TV tabs, search, result list, request flow).
Music/Lidarr is Phase 4. Card architecture should anticipate a third Music tab being added later.

</domain>

<decisions>
## Implementation Decisions

### Request confirmation flow
- Tapping "Request" opens a confirm dialog (not one-tap)
- Dialog shows: title, quality profile name, root folder path
- On confirm success: button changes to "Requested" (disabled, visually distinct color)
- On failure: inline error text on the result card, button resets to "Request" for retry

### In-library and status states
- Items already in Radarr/Sonarr show a green "In Library" badge — no request button shown
- In-library items appear mixed in search results at natural ranking (not sorted to bottom)
- Four visual states to distinguish:
  - **Available** (green) — in library and downloaded/available
  - **Monitored** (blue) — in library but not fully available (monitoring)
  - **Requested** (yellow) — just added, downloading or pending
  - **Not in library** — shows Request button
- Exact field mapping from arr lookup API response to these four states is Claude's discretion (researcher to investigate available fields)

### Result card layout and content
- Vertical list layout: one result per row, poster thumbnail on left, info on right
- Each card shows: 2:3 poster thumbnail, title, year, status badge or request button
- No overview snippet — keep it scannable
- Initial state (no query typed): empty card, just the search box visible
- Empty results state: plain text "No results for [query]"

### Search input behavior
- One shared search box at the top of the card (above tabs)
- Tab switch (Movies ↔ TV) immediately shows results for the same query in the other service — no re-typing
- 2-character minimum before search fires
- 300ms debounce (already specified in roadmap)
- Loading indicator: spinner in or directly below the search box; previous results stay visible while new ones load

### Claude's Discretion
- Exact spinner placement and styling
- Color values for the four status badge states (stay consistent with HA design system)
- Confirm dialog layout details (modal vs inline popover)
- Poster placeholder when image URL is missing or fails to load

</decisions>

<specifics>
## Specific Ideas

- The shared search box with per-tab results is designed to accommodate Phase 4's Music tab without structural refactoring
- Status badge color intent: green = have it, blue = watching for it, yellow = on its way, button = not yet

</specifics>

<deferred>
## Deferred Ideas

- Music/Lidarr tab UI — Phase 4
- Card editor (configurable quality profile / root folder per card) — Phase 5

</deferred>

---

*Phase: 03-movie-tv-request*
*Context gathered: 2026-02-27*
