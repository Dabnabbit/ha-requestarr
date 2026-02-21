# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** Search for media and submit requests to arr stack from a single HA dashboard card — no separate app, no separate auth, no separate container
**Current focus:** Template applied. Ready to customize for TMDB/Radarr/Sonarr/Lidarr.

## Current Position

Phase: 1 of 5 (Config Flow + API Clients)
Plan: 0 of 1 in current phase
Status: Ready to plan
Last activity: 2026-02-20 — ha-hacs-template v1.0 overlay applied via copier copy

Progress: [█░░░░░░░░░] 15% (scaffold + distribution satisfied by template)

## What the Template Provides (Already Done)

The ha-hacs-template v1.0 overlay (with `use_websocket=true`, `use_services=true`, `use_multi_step_config_flow=true`, `iot_class=cloud_polling`) satisfies:

- **SCAF-01**: Modern `async_register_static_paths` + `StaticPathConfig` (HA 2025.7+)
- **SCAF-02**: Valid `manifest.json` with `iot_class: cloud_polling`, `version`, `dependencies: [frontend, http, websocket_api]`
- **SCAF-03**: `unique_id` pattern with `_abort_if_unique_id_configured()` (needs customization to use TMDB key)
- **DIST-01**: HACS-compatible structure (hacs.json, manifest.json, file layout)
- **DIST-02**: Frontend card served via async static path registration
- **DIST-03**: CI workflows (hassfest + hacs/action) in `.github/workflows/validate.yml`

Also provides correct patterns for:
- Shared aiohttp session via `async_get_clientsession(hass)`
- `ConfigEntry.runtime_data` typed dataclass
- `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)`
- Multi-step config flow (user → credentials steps, expandable to 4 steps)
- WebSocket command handler registered in `async_setup`
- Service registration in `async_setup` (domain-scoped)
- `CoordinatorEntity` sensor base class
- Test scaffold (conftest, config_flow tests, coordinator tests, websocket tests)
- Options flow

## What Needs Customization (File-by-File)

### const.py
- Remove generic `DEFAULT_PORT` — Requestarr uses full URLs per service
- Add all CONF_ constants: `CONF_TMDB_API_KEY`, `CONF_RADARR_URL/API_KEY`, `CONF_SONARR_URL/API_KEY`, `CONF_LIDARR_URL/API_KEY`
- Add API base URLs: `TMDB_API_BASE`, `TMDB_IMAGE_BASE`
- Add `CONF_QUALITY_PROFILE_ID`, `CONF_ROOT_FOLDER_PATH` for each arr service

### api.py
- Replace generic `ApiClient` with multi-service client covering:
  - **TMDB**: search movie/TV, external_ids (TMDB→TVDB translation)
  - **Radarr v3**: movie count, add movie, quality profiles, root folders
  - **Sonarr v3**: series count, add series, quality profiles, root folders
  - **Lidarr v1** (note: v1 not v3!): artist count, add artist, quality profiles, root folders
  - **MusicBrainz**: artist search with mandatory `User-Agent` header + 1 req/sec rate limit
- Auth: TMDB uses `api_key` query param; arr uses `X-Api-Key` header; MusicBrainz uses `User-Agent`
- CRITICAL: Sonarr needs TVDB ID — requires TMDB `/tv/{id}/external_ids` translation

### config_flow.py
- Expand to 4-step flow: TMDB → Radarr (optional) → Sonarr (optional) → Lidarr (optional)
- Each arr step validates connection and fetches quality profiles + root folders
- `unique_id` from TMDB API key (not host:port)

### coordinator.py
- Poll library counts from all configured arr services every 5 min
- Return `{radarr_movies, sonarr_series, lidarr_artists}` (None for unconfigured)

### sensor.py
- 3 conditional sensors: Radarr movies, Sonarr series, Lidarr artists
- Only create sensors for configured services

### websocket.py
- 3 search commands: `requestarr/search_movies`, `search_tv`, `search_music`
- All search proxied through backend (TMDB key never exposed to card)

### services.py
- 3 request services: `request_movie` (Radarr), `request_series` (Sonarr+TVDB), `request_artist` (Lidarr)
- Use quality profiles + root folders from config

### services.yaml
- Schemas for all 3 request services

### frontend/requestarr-card.js
- Complete rewrite: Tabbed (Movies/TV/Music), search, results with posters, request buttons
- WebSocket for search, callService for requests

### strings.json + translations/en.json
- 4-step config flow descriptions

## Accumulated Context

### Decisions

- [Init]: iot_class is `cloud_polling` (TMDB is cloud API)
- [Init]: Sonarr requires TVDB ID translation from TMDB ID (3-step flow)
- [Init]: Lidarr uses /api/v1/, not /api/v3/ like Radarr/Sonarr
- [Init]: WebSocket commands for search (returns data to card)
- [Init]: Service calls for request submission (fire-and-forget with status)
- [Init]: MusicBrainz requires User-Agent header + 1 req/sec rate limit
- [Init]: Quality profiles + root folders fetched at config time, not hardcoded
- [Template]: Re-scaffolded from ha-hacs-template v1.0 (2026-02-20)

### Pending Todos

None yet.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-20
Stopped at: Template overlay complete, docs updated with customization guide
Resume action: Start Phase 1 — build API clients and multi-step config flow for TMDB + arr services
