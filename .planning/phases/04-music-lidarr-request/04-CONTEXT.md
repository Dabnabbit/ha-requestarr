# Phase 4: Music + Lidarr Request - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Activate the Music tab (disabled placeholder from Phase 3) with Lidarr artist search and request.
Scope: one new WebSocket command (`request_artist`) + Music tab UI wired to existing `search_music` command.
Full parity with Movies/TV tabs is the guiding principle across all decisions.

</domain>

<decisions>
## Implementation Decisions

### Circular avatar presentation
- Shape is locked (circular, Spotify convention — already in roadmap)
- Size: Claude's discretion — should match the row height of movie/TV rows (~60px diameter)
- Initials placeholder: first letter of artist name only (e.g. "T" for Taylor Swift, "M" for Metallica)
- Placeholder color: hash the artist name to pick deterministically from a fixed palette (Claude picks tasteful 8-12 color palette); same artist always gets the same color

### Artist result card content
- Show: circular avatar + artist name only (no genre tags, no album count, no "year")
- Layout: same vertical list as Movies/TV — one row per result, avatar left, info right
- Initial state (no query): empty card, just the search box (parity with Phase 3)
- Empty results: plain text "No results for [query]" (parity with Phase 3)

### Request confirm dialog
- Dialog shows: artist name + quality profile name + metadata profile name + root folder path
- Flow is identical to Phase 3: tap Request → confirm dialog → Confirm → button becomes "Requested"
- On success: button changes to "Requested" (disabled, yellow — parity with Phase 3)
- On failure: inline error text on result row, button resets to "Request" (parity with Phase 3)

### Library states and badge system
- Reuse Phase 3's four-state system: Available (green) / Monitored (blue) / Requested (yellow) / Request button
- "Requested" state is in-memory per search session — resets on new search (Phase 5 adds persistent arr library badges)
- State mapping from Lidarr lookup response follows same logic as Phase 3 (researcher to verify Lidarr's `has_file` / `statistics` fields)

### Claude's Discretion
- Avatar diameter (must feel proportionally consistent with 60×90 movie poster rows)
- Exact color palette for initials placeholders
- Whether `_getItemState()` in requestarr-card.js can be shared/extended for music vs. duplicated

</decisions>

<specifics>
## Specific Ideas

- "Near complete parity with movies/TV" — user explicitly wants Music tab to feel like a sibling of the Movies/TV tabs, not a different pattern
- The Music tab was already scaffolded as a disabled placeholder in Phase 3; this phase activates it without structural refactoring

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-music-lidarr-request*
*Context gathered: 2026-02-27*
