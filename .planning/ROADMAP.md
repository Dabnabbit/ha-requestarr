# Roadmap: Requestarr

## Overview

Requestarr delivers an HA-native media request card in 5 phases. The ha-hacs-template v1.0 overlay provides the scaffold, CI/CD, test framework, multi-step config flow, WebSocket framework, and service registration — eliminating the original Phase 1 (scaffold fixes) and Phase 7 (HACS distribution). The remaining work is domain-specific: API clients + config flow, sensors + search, movie/TV request flow, music search + Lidarr request, and library state detection + card polish. The build order follows hard dependencies: config flow gates API access, coordinator gates sensors, search gates request submission.

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

- [ ] **Phase 1: Config Flow + API Clients** — Multi-step config wizard (TMDB → Radarr → Sonarr → Lidarr), API client classes, coordinator
- [ ] **Phase 2: Sensors + Search** — Library count sensors, TMDB movie/TV search + MusicBrainz search via WebSocket
- [ ] **Phase 3: Movie & TV Request** — Radarr movie request, Sonarr TV request with TMDB→TVDB translation, card Movies/TV tabs
- [ ] **Phase 4: Music + Lidarr Request** — MusicBrainz search wiring, Lidarr artist request, card Music tab
- [ ] **Phase 5: Library State + Card Polish + Validation** — "Already in library" detection, card editor, tests, CI

## Phase Details

### Phase 1: Config Flow + API Clients
**Goal**: User can set up the integration with live API validation for TMDB and all arr services; coordinator polls library counts
**Depends on**: Template overlay (done)
**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, CONF-06, SENS-04
**Files to customize**:
  - `const.py` — All CONF_ constants, API base URLs, quality profile/root folder constants
  - `api.py` — Multi-service API client: TMDB, Radarr v3, Sonarr v3, Lidarr v1, MusicBrainz
  - `config_flow.py` — 4-step wizard: TMDB → Radarr (optional) → Sonarr (optional) → Lidarr (optional) with live validation
  - `coordinator.py` — Poll library counts from all configured arr services every 5 min
  - `strings.json` + `translations/en.json` — 4-step flow descriptions
  - `__init__.py` — Wire coordinator + clients into runtime_data
**Success Criteria**:
  1. Config flow validates TMDB API key with test search
  2. Config flow validates each arr service connection (optional skip)
  3. Quality profiles and root folders fetched and stored
  4. Coordinator polls library counts every 5 minutes

Plans:
- [ ] 01-01: Build API client classes and multi-step config flow with live validation

### Phase 2: Sensors + Search
**Goal**: Library count sensors visible in HA; WebSocket search commands return TMDB and MusicBrainz results
**Depends on**: Phase 1
**Requirements**: SENS-01, SENS-02, SENS-03, SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05
**Files to customize**:
  - `sensor.py` — 3 conditional sensors: Radarr movies, Sonarr series, Lidarr artists
  - `websocket.py` — 3 search commands: search_movies (TMDB), search_tv (TMDB), search_music (MusicBrainz)
**Success Criteria**:
  1. Library count sensors show correct values (only for configured services)
  2. Movie/TV search returns TMDB results with posters
  3. Music search returns MusicBrainz results
  4. TMDB API key never exposed to card/browser

Plans:
- [ ] 02-01: Implement sensors and WebSocket search commands

### Phase 3: Movie & TV Request
**Goal**: Users can request movies to Radarr and TV series to Sonarr from the card
**Depends on**: Phase 2
**Requirements**: REQT-01, REQT-02, REQT-04, CARD-01, CARD-02, CARD-03, CARD-04
**Files to customize**:
  - `services.py` — `request_movie` (Radarr POST) and `request_series` (TMDB→TVDB + Sonarr POST)
  - `services.yaml` — Movie and TV request schemas
  - `frontend/requestarr-card.js` — Tabbed card with Movies/TV tabs, search UI, results, request buttons
**Success Criteria**:
  1. Movie request adds to Radarr with correct quality profile + root folder
  2. TV request translates TMDB→TVDB ID and adds to Sonarr
  3. Card shows Movies/TV tabs with search and request flow
  4. TMDB poster thumbnails display in results

Plans:
- [ ] 03-01: Implement movie/TV request services with TVDB translation
- [ ] 03-02: Build card Movies/TV tabs with search and request UI

### Phase 4: Music + Lidarr Request
**Goal**: Users can search for music and request artists to Lidarr
**Depends on**: Phase 3
**Requirements**: SRCH-03 (card wiring), REQT-03
**Files to customize**:
  - `services.py` — Add `request_artist` (Lidarr POST with foreignArtistId/MBID)
  - `services.yaml` — Artist request schema
  - `frontend/requestarr-card.js` — Add Music tab
**Success Criteria**:
  1. MusicBrainz artist search returns results with User-Agent compliance
  2. Artist request adds to Lidarr with correct quality profile + root folder
  3. Music tab in card works end-to-end

Plans:
- [ ] 04-01: Implement Lidarr request service and Music card tab

### Phase 5: Library State + Card Polish + Validation
**Goal**: "Already in library" badges, visual card editor, tests, CI validation
**Depends on**: Phase 4
**Requirements**: REQT-05, CARD-05
**Files to customize**:
  - `coordinator.py` — Extend to fetch library TMDB/TVDB/MBID lists for state detection
  - `frontend/requestarr-card.js` — "In Library" badges on search results, visual card editor
  - `tests/` — Update all tests for Requestarr-specific logic
  - `README.md` — Final documentation
**Success Criteria**:
  1. Search results show "In Library" badge for media already in arr libraries
  2. Visual card editor configures all settings
  3. All tests pass, hassfest + hacs/action CI passes
  4. README documents installation, config flow, card usage, service examples

Plans:
- [ ] 05-01: Implement library state detection and "In Library" badges
- [ ] 05-02: Build card editor, update tests, validate CI

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Config Flow + API Clients | 0/1 | Not started | - |
| 2. Sensors + Search | 0/1 | Not started | - |
| 3. Movie & TV Request | 0/2 | Not started | - |
| 4. Music + Lidarr Request | 0/1 | Not started | - |
| 5. Library State + Card Polish + Validation | 0/2 | Not started | - |
