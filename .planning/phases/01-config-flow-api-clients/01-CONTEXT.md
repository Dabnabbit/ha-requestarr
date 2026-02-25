# Phase 1: Config Flow + API Clients - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

3-step config wizard (Radarr → Sonarr → Lidarr) with live API validation, uniform arr API client, coordinator polling library counts, options/reconfigure flows. No card UI, no search, no request submission — those are later phases.

</domain>

<decisions>
## Implementation Decisions

### Config step flow
- Each step is one arr service: Radarr → Sonarr → Lidarr
- Each step shows URL + API key fields only (no profile/folder selection in config)
- "I don't use this service" skip checkbox per step
- Auto-advance on successful validation (no confirmation toast)
- Inline field errors on validation failure (e.g., "Invalid API key" below the API key field)
- If user skips ALL services, block on the last step (Lidarr) with "At least one service must be configured"

### URL input handling
- User enters base URL only (e.g., `http://192.168.1.50:7878`)
- Integration appends `/api/v3/...` or `/api/v1/...` internally
- Support reverse proxy base paths (e.g., `https://media.example.com/radarr`)
- Strip trailing slashes from input
- Placeholder example in URL field (e.g., `http://192.168.1.50:7878`)

### Profile and folder selection
- Quality profiles, root folders, and metadata profiles (Lidarr) fetched at config time
- Use the arr service's own default profile as the selected default; fall back to first returned if none marked default
- Same approach for Lidarr metadata profile — use Lidarr's default
- Profiles stored in config entry data, not re-fetched automatically
- Manual "Refresh profiles" button in options flow for picking up changes

### Connection failure behavior
- Config-time: inline field errors (red text below field), user stays on step to fix
- Runtime: mark sensor entity unavailable on poll failure, auto-recover on next success (standard HA pattern)
- 10-second connection timeout for all arr API calls
- SSL certificate verification on by default, per-service toggle to disable (for self-signed certs)

### Options flow (gear icon)
- Dropdowns to change quality profile, root folder per configured service
- Dropdown for metadata profile (Lidarr only)
- "Verify SSL" toggle per service
- "Refresh profiles" button to re-fetch profiles/folders from arr services

### Reconfigure flow
- Full reconfigure: re-runs config wizard with current values pre-filled
- User can change URLs, API keys, skip/add services
- Only re-validate services whose URL or API key changed
- Unchanged services keep existing config without re-validation

### Coordinator
- Single DataUpdateCoordinator for all configured services
- Polls every 5 minutes
- Partial success: if one service fails, update others normally, mark failed service's sensor unavailable
- Does not fail the entire coordinator when one service is down

### Claude's Discretion
- Unique_id strategy (hash of first URL, all URLs, or singleton)
- Integration display name ("Requestarr" vs user-configurable)
- Coordinator poll data scope (counts only vs counts + system health)
- Exact error message wording for validation failures
- URL normalization edge cases (double slashes, trailing paths)

</decisions>

<specifics>
## Specific Ideas

- Placeholder URL examples per service: `http://192.168.1.50:7878` (Radarr), `:8989` (Sonarr), `:8686` (Lidarr)
- Lidarr uses `/api/v1/` not `/api/v3/` — API client must handle this per-service
- Arr services validate via `/system/status` endpoint
- `X-Api-Key` header for all arr API authentication

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-config-flow-api-clients*
*Context gathered: 2026-02-25*
