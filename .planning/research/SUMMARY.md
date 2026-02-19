# Research Summary: Requestarr

**Synthesized:** 2026-02-19
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md
**Confidence:** HIGH overall (Python/HA patterns confirmed against official docs; MEDIUM on Lidarr PR status and some community corroborations)

---

## Executive Summary

Requestarr is a Home Assistant HACS integration that embeds a Lovelace card enabling household members to search for and request movies, TV shows, and music directly from the HA dashboard — with no separate container, no separate auth, and no separate URL. The integration acts as a proxy layer: the card communicates exclusively with the HA backend (via WebSocket commands for search and HA services for request submission), the backend calls TMDB/MusicBrainz for search and Radarr/Sonarr/Lidarr for fulfillment. This architecture keeps API keys on the server side, leverages HA's native auth, and eliminates the primary pain point of tools like Jellyseerr: a separately-maintained container with its own auth stack.

The recommended build approach is zero pip dependencies (use HA's bundled `aiohttp` and `async_get_clientsession`), zero build toolchain (LitElement is borrowed from HA's own frontend at runtime), and strict adherence to 2025-era HA patterns: `async_register_static_paths` with `StaticPathConfig`, `runtime_data` on `ConfigEntry`, and WebSocket commands for any frontend operation that returns data. The scaffold this project is based on has two breaking bugs that must be fixed before any feature work: it calls the deprecated `register_static_path` (removed in HA 2025.7) and creates new `aiohttp.ClientSession` instances per coordinator cycle (session leak). Both are low-effort fixes that unblock everything else.

The project occupies a genuine gap in the ecosystem: no existing HA-native card supports submitting media requests, and no existing tool covers movies + TV + music (Lidarr) in a single integrated UI without a separate container. The differentiator stack — HA-native auth, HA mobile push notifications on fulfillment, Lidarr/MusicBrainz music support, and zero-container deployment — is achievable within a single-file frontend and a lean Python backend with no external pip dependencies.

---

## Key Findings

### From STACK.md

**Core technologies (all zero pip dependencies):**

| Technology | Rationale |
|------------|-----------|
| Python 3.12 (HA-bundled) | No choice; HA ships Python; do not install separately |
| `aiohttp` (HA-bundled via `async_get_clientsession`) | Already in HA virtualenv; creating new sessions per cycle leaks file descriptors |
| `voluptuous` (HA-bundled) | Standard for HA config flow schema validation; do not substitute pydantic |
| LitElement (HA-bundled, runtime extraction) | Zero build step; extracted from HA's own frontend at runtime |
| `DataUpdateCoordinator` + `CoordinatorEntity` | HA's standard pattern for polling integrations with multiple entities |

**Critical API facts:**
- Radarr and Sonarr are both `/api/v3/`; Lidarr uses `/api/v1/` (different version — common mistake)
- Radarr accepts TMDB IDs directly; Sonarr v3 requires TVDB IDs — TMDB results must be translated via TMDB's `/tv/{id}/external_ids` endpoint before a Sonarr POST
- MusicBrainz requires a descriptive `User-Agent` header and enforces 1 req/sec; music search is on-demand only (never polled)
- `async_register_static_paths([StaticPathConfig(...)])` is the only valid static path registration API as of HA 2025.7 — the sync version is removed

**Two patterns that replace old scaffold code:**
- `entry.runtime_data = coordinator` replaces `hass.data[DOMAIN][entry.entry_id]`
- `async_get_clientsession(hass)` replaces `async with aiohttp.ClientSession()`

### From FEATURES.md

**Clear market gap:** No HA-native card submits requests; no existing tool covers movies + TV + music in one UI without a separate container.

**P1 (launch-blocking) features:**
- Config flow with live connection validation (TMDB + each arr service)
- TMDB movie and TV search with rich result display (poster, title, year, overview)
- One-click movie request to Radarr
- One-click TV series request to Sonarr (with TMDB→TVDB ID translation)
- MusicBrainz artist search with result display
- One-click artist request to Lidarr
- "Already in library" indicator for all three media types
- HA mobile push notification on fulfillment
- Visual card editor (quality profile default, root folder, header text)
- Working HACS distribution (CI green, tagged release)

**P2 (add after validation):**
- "Already requested" indicator (lightweight HA storage-backed store)
- Per-tab search state persistence

**Defer to v2+ (do not build now):**
- Trending/discover browse (Mediarr already covers display; large scope)
- Season-level TV request granularity
- Per-user quotas and approval workflow
- 4K quality picker per-request
- Request history and analytics

**Anti-features to explicitly reject:**
- Real-time search-as-you-type (TMDB rate limit, complexity)
- Multiple arr instance routing (single instance per service is the target household model)
- Plex integration (explicitly out of scope; use Overseerr)
- Jellyfin library display (use Mediarr; Requestarr stays request-focused)

### From ARCHITECTURE.md

**Component map:**

| Component | Responsibility |
|-----------|----------------|
| `config_flow.py` | 4-step wizard (TMDB → Radarr → Sonarr → Lidarr) with live API validation per step |
| `coordinator.py` | Polls arr library counts every 5 min; exposes `async_search()` and `async_request_*()` methods |
| `sensor.py` | Exposes coordinator data as HA sensor entities (library counts in `hass.states`) |
| `__init__.py` | Wires coordinator to sensors; registers WebSocket commands; registers static path for card JS |
| `requestarr-card.js` | Single-file LitElement card; tabbed UI; reads sensor state; calls WebSocket commands |

**Two communication patterns (non-negotiable):**
1. **WebSocket `sendMessagePromise` for search** — the only way to return data from HA backend to the card; services are fire-and-forget and cannot return results
2. **`hass.callService` for request submission** — fire-and-forget is appropriate here; optimistic UI shows "Requested" badge immediately

**Build order driven by dependencies:**
Phase 1 (scaffold fixes) → Phase 2 (config flow + coordinator base) → Phase 3 (sensors) → Phase 4 (search WebSocket) → Phase 5 (request services) → Phase 6 (card search UI) → Phase 7 (card request UI) → Phase 8 (library state detection)

**Critical Sonarr integration detail:** TMDB search → TMDB `/tv/{id}/external_ids` → Sonarr `/api/v3/series/lookup` → Sonarr POST `/api/v3/series`. Three steps, not one.

**Arr add payload requirement:** All three arr services require `qualityProfileId` and `rootFolderPath` (and more) in the POST body — these must be fetched from each service at config time and cached. Hardcoding `qualityProfileId=1` fails silently.

### From PITFALLS.md

**Critical pitfalls (project-blocking if missed):**

| Pitfall | Prevention |
|---------|-----------|
| Sonarr requires TVDB ID, not TMDB ID | 3-step request flow: TMDB search → TMDB external_ids → Sonarr lookup → Sonarr POST |
| `register_static_path` removed in HA 2025.7 | Replace with `async_register_static_paths([StaticPathConfig(...)])` in Phase 1 |
| `aiohttp.ClientSession()` per coordinator cycle = session leak | Replace with `async_get_clientsession(hass)` stored as `self._session` in Phase 1 |
| Arr POST missing required fields (qualityProfileId, rootFolderPath, images, title) | Fetch arr defaults at config time; use lookup response to build full POST body |
| MusicBrainz blocks without descriptive User-Agent header | Set `User-Agent: Requestarr/x.x.x (github.com/Dabentz/ha-requestarr)` on all MB requests |

**Moderate pitfalls (must fix, non-blocking to start):**

| Pitfall | Prevention |
|---------|-----------|
| TMDB API key exposed if card calls TMDB directly from JS | All TMDB calls proxied through backend WebSocket command |
| `iot_class: "local_polling"` wrong when TMDB (cloud) is required | Change to `"cloud_polling"` in manifest.json |
| Config flow missing `unique_id` → duplicate integration entries | Add `async_set_unique_id` + `_abort_if_unique_id_configured` to `async_step_user` |
| No options/reconfigure flow → users cannot update credentials | Implement `async_step_reconfigure` before HACS submission |
| `hass.callService` used for search → no return path | Use `hass.callWS` (`sendMessagePromise`) for search; `callService` only for request submission |
| `strings.json` and `en.json` drift → hassfest CI fails | Treat translation sync as definition-of-done for every config flow change |

---

## Implications for Roadmap

The research strongly suggests a 6-phase structure with a mandatory Phase 0 to eliminate scaffold technical debt before feature work begins. The phase order is driven by hard dependencies: the static path bug blocks card loading; the session leak causes coordinator instability; config flow must validate before the coordinator can use those credentials; sensors must exist before the card can read them; search WebSocket must exist before the card search UI can be built.

### Suggested Phase Structure

**Phase 1 — Scaffold Fixes (Pre-requisite, all blockers)**
Fix the two breaking scaffold bugs that will fail all HA 2025.7+ installs and cause coordinator instability. Also fix `iot_class`, `FRONTEND_SCRIPT_URL`, and `unique_id` stubs in config flow. These are not features — they are correctness prerequisites.
- Replace `register_static_path` with `async_register_static_paths([StaticPathConfig(...)])`
- Replace all `aiohttp.ClientSession()` instances with `async_get_clientsession(hass)` / `self._session`
- Change `iot_class` to `"cloud_polling"` in manifest.json
- Resolve `FRONTEND_SCRIPT_URL` strategy (integration-owned `/requestarr/...` path vs HACS-owned `/hacsfiles/...`)
- Add `async_set_unique_id` to config flow
- Validate: `hassfest` CI passes, integration loads on HA 2025.7+ without deprecation warnings
- **Research flag:** Standard patterns — no phase research needed

**Phase 2 — Config Flow + Coordinator Foundation**
Implement the 4-step config flow with real live validation (TMDB API test, Radarr connection test, Sonarr connection test, Lidarr connection test). Fetch and cache arr defaults (quality profiles, root folders, metadata profiles) at config time. Implement coordinator base with library count polling.
- Features covered: Config flow with connection validation, library count sensors (P1)
- Pitfalls to avoid: Multi-step chaining bug (validation inside `user_input is not None` guard), config flow calling API in form-display branch, missing translation sync
- Deliverable: Integration installs without error; sensors show real library counts
- **Research flag:** Standard HA patterns — no phase research needed

**Phase 3 — Search: Movies and TV**
Implement the search WebSocket command backend (`requestarr/search` for `movie` and `tv`). Wire the card's `_doSearch()` to `hass.connection.sendMessagePromise`. Display results with poster, title, year, and truncated overview.
- Features covered: TMDB movie search, TMDB TV search, search result display (P1)
- Pitfalls to avoid: TMDB key in JS (never), `callService` for search (use WebSocket), unbounded results (cap at 20)
- Deliverable: Card search returns results for movies and TV
- **Research flag:** Standard patterns — no phase research needed

**Phase 4 — Request Submission: Movies and TV**
Implement Radarr movie request (lookup → fetch profiles → POST) and Sonarr TV request (TMDB search → TMDB external_ids for TVDB ID → Sonarr lookup → Sonarr POST). Wire card's `_requestItem()` to `hass.callService`. Add optimistic "Requested" UI state.
- Features covered: One-click Radarr request, one-click Sonarr request (P1)
- Pitfalls to avoid: Sonarr TVDB ID requirement (critical), hardcoded qualityProfileId, POST body missing required fields
- Deliverable: Movie and TV requests submit successfully to Radarr and Sonarr
- **Research flag:** Sonarr 3-step flow is non-obvious; validate against a live Sonarr instance early

**Phase 5 — Music: MusicBrainz Search + Lidarr Request**
Implement MusicBrainz artist search (separate path from TMDB; requires User-Agent header). Add `music` case to search WebSocket command. Implement Lidarr artist request (MusicBrainz MBID → Lidarr lookup → Lidarr POST). Wire music tab in card.
- Features covered: Music search, one-click Lidarr request (P1 — key differentiator)
- Pitfalls to avoid: MusicBrainz User-Agent (mandatory), Lidarr `/api/v1/` not `/api/v3/`, `foreignArtistId` is MBID string not int, metadataProfileId required, never poll MusicBrainz
- Deliverable: Music tab searches artists and submits to Lidarr
- **Research flag:** Lidarr `metadataProfileId` fetch pattern warrants a quick phase research pass — less documented than Radarr/Sonarr

**Phase 6 — Library State + Push Notifications**
Extend coordinator polling to fetch arr library IDs (not just counts) for "already in library" detection. Implement ID matching (TMDB ID for movies, TVDB ID for TV, MBID for music). Add HA push notification on request fulfillment (coordinator detects download state change → HA notify service). Add visual card editor config.
- Features covered: "Already in library" indicator (all three media types), HA push notification on fulfillment, visual card editor (P1)
- Pitfalls to avoid: Loading full arr library vs count-only (cap response size), coordinator poll frequency (5 min may be too slow for near-real-time state; trigger refresh after request submission)
- Deliverable: Cards show "In Library" / "Requested" badges; push notification fires on availability
- **Research flag:** HA notification automation trigger patterns — worth a phase research pass to identify best trigger mechanism (state change vs event vs coordinator-direct call)

**Phase 7 — Polish + HACS Submission Prep**
Add `async_step_reconfigure` to allow credential updates. Add `device_info` to sensors for device grouping. Implement "already requested" indicator with HA storage persistence. Sync `strings.json` / `en.json` with any additions. Verify hassfest and HACS action CI both pass. Submit PR to `home-assistant/brands` for HACS default store listing.
- Features covered: Reconfigure flow, already-requested indicator (P2), sensor device grouping
- Pitfalls to avoid: Options flow using deprecated `config_entry` parameter (use `reconfigure` pattern), brands PR timing
- Deliverable: Integration ready for public HACS submission
- **Research flag:** Standard patterns — no phase research needed

---

## Research Flags

| Phase | Research Needed? | Reason |
|-------|-----------------|--------|
| Phase 1 — Scaffold Fixes | No | Standard HA deprecation migration; patterns are documented |
| Phase 2 — Config Flow + Coordinator | No | Standard `ConfigFlow` + `DataUpdateCoordinator` patterns; well-documented |
| Phase 3 — Search | No | WebSocket command pattern is documented; TMDB search is straightforward |
| Phase 4 — Movie + TV Requests | **Validate against live Sonarr** | 3-step Sonarr flow (TMDB → external_ids → Sonarr lookup → POST) has documented pitfalls but real response shapes should be verified against an actual Sonarr v3 instance before implementation |
| Phase 5 — Music + Lidarr | **Yes — Lidarr metadataProfileId** | Lidarr's required fields for POST `/api/v1/artist` are less documented than Radarr/Sonarr; `metadataProfileId` fetch pattern and valid values need verification against Lidarr's OpenAPI spec or a live instance |
| Phase 6 — Library State + Notifications | **Yes — notification trigger mechanism** | The right HA pattern for coordinator-initiated push notifications (state change event vs direct `hass.services.call("notify", ...)` from coordinator vs automation) has tradeoffs worth researching before committing to an approach |
| Phase 7 — Polish + HACS Prep | No | Standard HA reconfigure pattern; brands submission is procedural |

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Stack | HIGH | Python/HA patterns verified against official HA developer docs; API endpoints verified against official Radarr/Sonarr/Lidarr docs |
| Features | MEDIUM-HIGH | Competitive landscape from secondary sources (rapidseedbox, community posts); scaffold inspected directly (HIGH); Lidarr PR status in Seerr is MEDIUM (open PR, merge unconfirmed) |
| Architecture | HIGH | Patterns verified against HA developer docs; WebSocket command pattern is documented with examples; scaffold structure inspected directly |
| Pitfalls | HIGH | Most critical pitfalls confirmed by official HA devblog posts and GitHub issues with multiple corroborating replies; aiohttp session leak confirmed by HA community thread |

**Overall confidence: HIGH**

The two areas of uncertainty are:
1. Exact Lidarr `POST /api/v1/artist` required fields — official docs exist but are less battle-tested than Radarr/Sonarr community documentation. Should be validated against a live Lidarr instance during Phase 5.
2. Notification trigger mechanism — multiple valid approaches exist in HA; the right one depends on whether notifications should fire from within the coordinator, from a triggered automation, or from a HA script. Phase 6 research will resolve this.

---

## Gaps to Address During Planning

1. **Sonarr POST body shape:** The lookup-then-add pattern is confirmed, but the exact set of fields from the lookup response that must be echoed back in the POST body (seasons array, images, etc.) should be validated against a live Sonarr v3 instance before Phase 4 implementation starts.

2. **Lidarr metadataProfileId:** Confirmed required; fetch pattern from `/api/v1/metadataprofile` is the assumed approach. Validate this against Lidarr's OpenAPI spec or a live instance — the field may have a different name or structure than expected.

3. **HA push notification delivery path:** Three options identified (coordinator → `hass.services.call("notify")` directly, coordinator → state change → user-created automation, coordinator → HA event → integration-registered automation). Each has different tradeoffs for user configurability vs implementation complexity. Needs decision before Phase 6.

4. **`hass.callWS` vs `hass.connection.sendMessagePromise`:** The architecture research uses `sendMessagePromise`; the pitfalls research uses `hass.callWS`. These are functionally equivalent (both call the same WebSocket message API) but `hass.callWS` is the public-facing method on the `hass` object in custom cards. Confirm which is the current recommended API in HA 2025+ custom card development documentation.

5. **HACS brands registration timeline:** The integration needs a PR in `home-assistant/brands` to appear in the HACS default store. This is procedural but has a review queue. Should be submitted early (after Phase 2 produces a working integration) rather than waiting for full feature completion.

---

## Aggregated Sources

**Official Documentation (HIGH confidence):**
- Home Assistant Developer Docs — `async_register_static_paths`: https://developers.home-assistant.io/blog/2024/06/18/async_register_static_paths/
- Home Assistant Developer Docs — `runtime_data` quality scale rule: https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/runtime-data/
- Home Assistant Developer Docs — WebSocket API extension: https://developers.home-assistant.io/docs/frontend/extending/websocket-api/
- Home Assistant Developer Docs — Integration service actions: https://developers.home-assistant.io/docs/dev_101_services/
- Home Assistant Developer Docs — Config flow handler: https://developers.home-assistant.io/docs/config_entries_config_flow_handler/
- Home Assistant Developer Docs — Inject websession (`async_get_clientsession`): https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/inject-websession/
- Home Assistant Developer Docs — Custom card development: https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/
- HACS integration publishing: https://www.hacs.xyz/docs/publish/integration/
- Radarr API v3: https://radarr.video/docs/api/
- Sonarr API v3: https://sonarr.tv/docs/api/
- Lidarr API v1: https://lidarr.audio/docs/api/
- MusicBrainz API and rate limiting: https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
- TMDB API getting started: https://developer.themoviedb.org/docs/getting-started

**GitHub Issues (HIGH confidence — confirmed behaviors):**
- Sonarr TVDB ID requirement: https://github.com/Sonarr/Sonarr/issues/7565
- Radarr required fields: https://github.com/Radarr/Radarr/issues/7095, https://github.com/Radarr/Radarr/issues/5881
- HACS `register_static_path` deprecation: https://github.com/hacs/integration/issues/3828
- HACS options flow `config_entry` deprecation: https://github.com/hacs/integration/issues/4314

**Community Sources (MEDIUM confidence):**
- Jellyseerr/Overseerr/Seerr feature documentation: rapidseedbox.com, docs.jellyseerr.dev, seerr.dev
- Mediarr card: github.com/Vansmak/mediarr-card
- HA community — DataUpdateCoordinator instability after hours: https://community.home-assistant.io/t/dataupdatecoordinator-based-integrations-become-unavailable-after-a-few-hours/986502

**Direct Inspection (HIGH confidence):**
- Existing scaffold: `/home/dab/Projects/ha-requestarr/custom_components/requestarr/`

---

*Research synthesized for: Requestarr — Home Assistant HACS media request integration*
*Synthesized: 2026-02-19*
