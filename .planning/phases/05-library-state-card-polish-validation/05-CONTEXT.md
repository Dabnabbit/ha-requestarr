# Phase 5: Library State + Card Polish + Validation - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

"In Library" green badges on search results, a visual Lovelace card editor, pytest unit test coverage, and CI validation (hassfest + hacs/action). New capabilities (e.g., album-level Lidarr search, bulk request, collections) belong in future phases.

</domain>

<decisions>
## Implementation Decisions

### In-Library item behavior
- `id > 0` from arr lookup response = "In Library" — applies to all three media types
- Request button is grayed out and shows "In Library" text when item is in library — not hidden, not clickable
- For TV shows: treat as "In Library" if the show exists (id > 0), regardless of missing seasons/episodes
- For Lidarr: check at artist level only — if artist has id > 0, badge appears; no album-level granularity
- Search results keep original arr relevance order — no re-sorting of in-library items to bottom
- Behavior is consistent across movies, TV shows, and music (same badge, same button treatment)

### Card editor scope
- Visual editor exposes: service toggles (which tabs to show) + display options only
- Only services that are actually configured in the integration appear as toggleable options in the editor — unconfigured services are not shown
- Editor structure: fields + save button only (no live preview pane)
- Card title/header handling: Claude's discretion

### Badge visual design
- Green badge (not HA theme color) — universally understood as "available/present"
- Badge is a pill overlay on the poster/thumbnail, consistent across movies, TV, and music results
- Disabled button state: grayed out with "In Library" text (button stays visible to communicate why it can't be clicked)
- Result ordering unchanged — no sorting by library state

### Test strategy
- Primary goal: pytest unit tests covering logic + eventual hassfest/hacs CI compliance
- Local fallback when GHA hours exhausted: `pytest` from repo root + manual HA reload in dev environment
- Coverage areas (all four required):
  1. Config flow validation — each wizard step, error states, skip logic
  2. Coordinator + API client — polling, ArrClient requests, timeout/error handling
  3. WebSocket commands — search, result normalization, in_library detection, error responses
  4. Request flow — add-to-arr payload building, profile lookup, error handling (Phases 3+4 logic)
- Mock approach: inline mock data in test functions (not JSON fixture files)

### Claude's Discretion
- Card title/header — whether to show one, its default value, and whether it's in the editor
- Badge placement specifics (top-right vs bottom-left on poster)
- Loading skeleton and error state styling
- pytest directory structure and test file naming

</decisions>

<specifics>
## Specific Ideas

- User emphasized consistency repeatedly: same badge behavior, same button treatment, same visual design across movies, TV, and music — don't diverge between media types
- GHA minutes may be exhausted at time of Phase 5 execution — plan must include instructions for running tests locally with pytest, not just CI
- CI goal is hassfest + hacs/action compliance (same as prior phases)

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-library-state-card-polish-validation*
*Context gathered: 2026-02-27*
