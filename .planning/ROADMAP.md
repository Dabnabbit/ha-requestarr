# Roadmap: Requestarr

## Overview

Requestarr delivers an HA-native media request card in 5 phases. The ha-hacs-template v1.0 overlay provides the scaffold, CI/CD, test framework, multi-step config flow, WebSocket framework, and service registration. All search uses arr lookup endpoints directly (Radarr, Sonarr, Lidarr) — no TMDB key or MusicBrainz client needed. The arr services proxy upstream metadata and return public CDN image URLs.

## Template Baseline (Satisfied by ha-hacs-template v1.0)

| Requirement | What the Template Provides |
|-------------|---------------------------|
| SCAF-01 | `async_register_static_paths` + `StaticPathConfig` (HA 2025.7+) |
| SCAF-02 | Valid manifest.json with `iot_class: cloud_polling`, `version`, `dependencies: [frontend, http, websocket_api]` |
| SCAF-03 | `unique_id` + `_abort_if_unique_id_configured()` pattern |
| DIST-01 | HACS-compatible file structure (hacs.json, manifest.json) |
| DIST-02 | Frontend card served via async static path registration |
| DIST-03 | CI workflows (hassfest + hacs/action) in `.github/workflows/validate.yml` |

## Phases

- [x] **Phase 1: Config Flow + API Clients** — 3-step config wizard (Radarr → Sonarr → Lidarr), uniform arr API client, coordinator
- [x] **Phase 2: Sensors + Search** — Library count sensors, search via arr lookup endpoints through WebSocket
- [x] **Phase 3: Movie & TV Request** — Radarr movie request, Sonarr TV request (tvdbId in lookup), card Movies/TV tabs (2026-02-27)
- [ ] **Phase 4: Music + Lidarr Request** — Lidarr artist lookup search, Lidarr artist request, card Music tab with circular avatars
- [ ] **Phase 5: Library State + Card Polish + Validation** — "Already in library" badges, card editor, tests, CI

## Phase Details

### Phase 1: Config Flow + API Clients
**Goal**: User can set up the integration with live API validation for all arr services; coordinator polls library counts
**Depends on**: Template overlay (done)
**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, SENS-04
**Files to customize**:
  - `const.py` — All CONF_ constants, arr API path constants, quality profile/root folder constants
  - `api.py` — Uniform arr API client: all services use X-Api-Key header, system/status for validation, lookup for search, POST for add
  - `config_flow.py` — 3-step wizard: Radarr (optional) → Sonarr (optional) → Lidarr (optional) with live validation; fetch quality profiles + root folders + metadata profiles (Lidarr)
  - `coordinator.py` — Poll library counts from all configured arr services every 5 min
  - `strings.json` + `translations/en.json` — 3-step flow descriptions
  - `__init__.py` — Wire coordinator + clients into runtime_data
**Success Criteria**:
  1. Config flow validates each arr service connection (optional skip, at least one required)
  2. Quality profiles, root folders, and metadata profiles fetched and stored
  3. Coordinator polls library counts every 5 minutes
  4. No TMDB key step — arr services are the only external dependency

Plans:
- [x] 01-01: Build uniform arr API client and 3-step config flow with live validation

### Phase 2: Sensors + Search
**Goal**: Library count sensors visible in HA; WebSocket search commands return arr lookup results with public CDN image URLs
**Depends on**: Phase 1
**Requirements**: SENS-01, SENS-02, SENS-03, SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05
**Files to customize**:
  - `sensor.py` — 3 conditional sensors: Radarr movies, Sonarr series, Lidarr artists
  - `websocket.py` — 3 search commands using arr lookup endpoints: search_movies (Radarr), search_tv (Sonarr), search_music (Lidarr)
**Success Criteria**:
  1. Library count sensors show correct values (only for configured services)
  2. Movie search returns Radarr lookup results with TMDB CDN poster URLs
  3. TV search returns Sonarr lookup results with TheTVDB CDN poster URLs
  4. Music search returns Lidarr lookup results with fanart.tv CDN image URLs
  5. Arr API keys never exposed to card/browser — only public CDN URLs sent to frontend

Plans:
- [x] 02-01: Implement sensors and WebSocket search commands via arr lookup endpoints

### Phase 3: Movie & TV Request
**Goal**: Users can request movies to Radarr and TV series to Sonarr from the card
**Depends on**: Phase 2
**Requirements**: REQT-01, REQT-02, REQT-04, CARD-01, CARD-02, CARD-03, CARD-04
**Files to customize**:
  - `websocket.py` — Add `request_movie` (Radarr POST) and `request_series` (Sonarr POST with tvdbId from lookup — no TMDB translation needed)
  - `frontend/requestarr-card.js` — Tabbed card with Movies/TV tabs, 300ms debounce search, poster results (2:3 rectangle), request buttons, green/blue/yellow/red status badges
**Success Criteria**:
  1. Movie request adds to Radarr with correct quality profile + root folder
  2. TV request adds to Sonarr using tvdbId from lookup response (no extra API call)
  3. Card shows Movies/TV tabs with search and request flow
  4. Public CDN poster thumbnails display in results (rewrite TMDB to w342)

Plans:
- [x] 03-01: Implement movie/TV request via WebSocket commands
- [x] 03-02: Build card Movies/TV tabs with search and request UI

### Phase 4: Music + Lidarr Request
**Goal**: Users can search for music artists and request them to Lidarr
**Depends on**: Phase 3
**Requirements**: SRCH-03 (card wiring), REQT-03
**Files to customize**:
  - `websocket.py` — Add `request_artist` (Lidarr POST with foreignArtistId + metadataProfileId)
  - `frontend/requestarr-card.js` — Add Music tab with circular avatar thumbnails (Spotify convention), initials placeholder with deterministic color for missing fanart.tv images
**Success Criteria**:
  1. Lidarr artist lookup returns results with fanart.tv images where available
  2. Artist request adds to Lidarr with correct quality profile + metadata profile + root folder
  3. Music tab uses circular avatars (not rectangular posters) to match streaming app convention
  4. Initials-based placeholder works for artists without fanart.tv images (~40-60%)

Plans:
- [ ] 04-01: Implement Lidarr request and Music card tab with circular avatars

### Phase 5: Library State + Card Polish + Validation
**Goal**: "Already in library" badges, visual card editor, tests, CI validation
**Depends on**: Phase 4
**Requirements**: REQT-05, CARD-05
**Files to customize**:
  - `frontend/requestarr-card.js` — "In Library" green badges on search results (id > 0 from lookup), visual card editor
  - `tests/` — Update all tests for Requestarr-specific logic
  - `README.md` — Final documentation
**Success Criteria**:
  1. Search results show "In Library" green badge when arr lookup returns id > 0
  2. Visual card editor configures all settings
  3. All tests pass, hassfest + hacs/action CI passes
  4. README documents installation, config flow, card usage

Plans:
- [ ] 05-01: Implement library state detection and "In Library" badges
- [ ] 05-02: Build card editor, update tests, validate CI

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Config Flow + API Clients | 1/1 | Complete | 2026-02-25 |
| 2. Sensors + Search | 1/1 | Complete | 2026-02-27 |
| 3. Movie & TV Request | 0/2 | Not started | - |
| 4. Music + Lidarr Request | 0/1 | Not started | - |
| 5. Library State + Card Polish + Validation | 0/2 | Not started | - |
