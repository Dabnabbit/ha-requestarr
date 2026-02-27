# Phase 2: Sensors + Search - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Library count sensors visible in HA for each configured arr service. WebSocket search commands call arr lookup endpoints and return structured results with public CDN image URLs. Three separate search commands (movies, TV, music) return minimal but forward-looking payloads that include data needed by Phases 3-5.

</domain>

<decisions>
## Implementation Decisions

### Search Result Payload
- Minimal fields per result: title, year, poster URL, full overview text (card truncates via CSS)
- Rewrite TMDB poster URLs from `/t/p/original/` to `/t/p/w300/` for card-sized thumbnails; TheTVDB and fanart.tv URLs passed through as-is
- Three separate WebSocket commands: `search_movies`, `search_tv`, `search_music` — card calls the one matching its active tab
- Send full overview text; card handles truncation with CSS line-clamp (more flexible across screen sizes)

### Sensor Design
- Sensor state value = service status (connected / disconnected / error), not the library count
- Attributes: library count, service URL (masked/redacted), last successful sync time
- One sensor per configured service only: `sensor.requestarr_radarr`, `sensor.requestarr_sonarr`, `sensor.requestarr_lidarr`
- No combined/parent sensor
- Service-specific MDI icons: `mdi:movie` (Radarr), `mdi:television` (Sonarr), `mdi:music` (Lidarr)

### Search Error Handling
- Structured error responses with distinct error codes:
  - `service_not_configured` — service wasn't set up in config flow
  - `service_unavailable` — service is configured but not responding
  - `invalid_query` — empty/blank search query rejected
- Cap search results at 20 per query (arr APIs can return 50+)
- Reject empty search queries with error (card handles debounce/validation before calling)

### Result Pre-tagging
- Include `in_library` boolean flag (derived from arr `id > 0`) in every search result — card can ignore until Phase 5
- Include `arr_id` (integer or null) for items already in library — enables future deep links to arr web UI
- Always include external IDs needed for requesting: `tmdbId` (movies), `tvdbId` (TV), `foreignArtistId` (music) — avoids redundant lookups in Phases 3-4
- Include default quality profile name and root folder path in search results — card has everything needed for one-click request without extra WebSocket calls

### Claude's Discretion
- WebSocket command naming convention and registration pattern
- Exact sensor entity ID format and device info structure
- Error response JSON shape (as long as it includes error code + message)
- Coordinator update interval (currently 5 min from Phase 1)

</decisions>

<specifics>
## Specific Ideas

- Search results should be self-contained for the request flow: a card receiving a search result should have all data needed to display it AND submit a request, without making additional WebSocket calls
- Sensor status approach (connected/disconnected) was chosen over plain count because it enables HA automations for service health monitoring (e.g., notify when Radarr goes down)
- Image URL rewriting is backend-only (w300 for TMDB) — card receives ready-to-use URLs

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-sensors-search*
*Context gathered: 2026-02-27*
