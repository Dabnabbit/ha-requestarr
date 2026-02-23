# Requirements: Requestarr

**Defined:** 2026-02-19
**Updated:** 2026-02-23 (arr-lookup architecture replaces TMDB/MusicBrainz direct calls)
**Core Value:** Users can search for media and submit requests to their arr stack from a single HA dashboard card — no separate app, no separate auth, no separate container.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Scaffold & Foundation (Satisfied by Template)

- [x] **SCAF-01**: Integration loads on HA 2025.7+ without deprecation warnings (async static paths, shared aiohttp session) — *Template: async_register_static_paths, async_get_clientsession*
- [x] **SCAF-02**: `manifest.json` passes hassfest validation (correct `iot_class: cloud_polling`, `version`, `unique_id` support) — *Template: correct manifest with dependencies [frontend, http, websocket_api]*
- [x] **SCAF-03**: Config entry has unique_id to prevent duplicate entries — *Template: unique_id + _abort_if_unique_id_configured() pattern (customize to use first arr service URL)*

### Configuration

- [ ] **CONF-01**: User can configure Radarr connection (URL, API key) with live validation via `/api/v3/system/status`
- [ ] **CONF-02**: User can configure Sonarr connection (URL, API key) with live validation via `/api/v3/system/status`
- [ ] **CONF-03**: User can configure Lidarr connection (URL, API key) with live validation via `/api/v1/system/status`
- [ ] **CONF-04**: Each arr service is optional (user can skip Radarr, Sonarr, or Lidarr) but at least one must be configured
- [ ] **CONF-05**: Quality profile, root folder, and metadata profile (Lidarr) fetched from each arr service at config time

### Sensors

- [ ] **SENS-01**: Radarr movie count sensor shows total movies in library
- [ ] **SENS-02**: Sonarr series count sensor shows total TV series in library
- [ ] **SENS-03**: Lidarr artist count sensor shows total artists in library
- [ ] **SENS-04**: Sensors update via DataUpdateCoordinator polling every 5 minutes

### Search

- [ ] **SRCH-01**: User can search for movies via Radarr lookup endpoint (`/api/v3/movie/lookup`) through WebSocket command
- [ ] **SRCH-02**: User can search for TV shows via Sonarr lookup endpoint (`/api/v3/series/lookup`) through WebSocket command
- [ ] **SRCH-03**: User can search for music artists via Lidarr lookup endpoint (`/api/v1/artist/lookup`) through WebSocket command
- [ ] **SRCH-04**: Search results display poster/avatar thumbnail (from public CDN URLs in response), title, year, and description
- [ ] **SRCH-05**: Arr API keys stay server-side (never exposed to card JavaScript); card uses public CDN image URLs from `remoteUrl`/`remotePoster` fields

### Requests

- [ ] **REQT-01**: User can request a movie to Radarr with one click (POST `/api/v3/movie` with tmdbId from lookup)
- [ ] **REQT-02**: User can request a TV series to Sonarr with one click (POST `/api/v3/series` with tvdbId already in lookup response — no TMDB translation needed)
- [ ] **REQT-03**: User can request a music artist to Lidarr with one click (POST `/api/v1/artist` with foreignArtistId from lookup)
- [ ] **REQT-04**: Request uses quality profile and root folder from config (not hardcoded)
- [ ] **REQT-05**: "Already in library" indicator from arr lookup response (id > 0 means in library)

### Card UI

- [ ] **CARD-01**: Lovelace card with tabbed interface (Movies / TV / Music)
- [ ] **CARD-02**: Search input with 300ms debounce (Jellyseerr pattern)
- [ ] **CARD-03**: Search results: poster-centric list for Movies/TV (2:3 rectangle), text-centric list with circular avatars for Music
- [ ] **CARD-04**: Request button on each result with visual feedback — green/blue/yellow/red status badge system (Jellyseerr pattern)
- [ ] **CARD-05**: Visual card editor for configuration

### Distribution (Satisfied by Template)

- [x] **DIST-01**: HACS-compatible (hacs.json, manifest.json, correct file structure) — *Template: correct structure*
- [x] **DIST-02**: Frontend card served via integration's async static path registration — *Template: StaticPathConfig in async_setup()*
- [x] **DIST-03**: CI passes hassfest and hacs/action validation — *Template: .github/workflows/validate.yml*

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Features

- **ENHC-01**: "Already requested" indicator with persistent state tracking
- **ENHC-02**: HA push notification when requested media becomes available
- **ENHC-03**: Per-tab search state persistence (switching tabs retains results)
- **ENHC-04**: Reconfigure flow to update credentials without removing integration
- **ENHC-05**: Album-level music requests (select specific albums from artist detail)

### Advanced

- **ADVN-01**: Season-level TV request granularity
- **ADVN-02**: 4K quality picker per-request
- **ADVN-03**: Trending/discover media browse
- **ADVN-04**: Request history and analytics
- **ADVN-05**: Per-user request quotas and approval workflow

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct TMDB API calls | Arr lookup endpoints return same data with richer metadata |
| Direct MusicBrainz API calls | Lidarr lookup provides superset including images + bio |
| Real-time search-as-you-type | 300ms debounce is sufficient; arr services are on LAN |
| Multiple arr instance routing | Single instance per service is the target household model |
| Plex integration | Jellyfin-only household; use Overseerr for Plex |
| Jellyfin library display | Use Mediarr card; Requestarr stays request-focused |
| Now-playing / currently-streaming | Different feature; Mediarr covers this |
| Mobile-specific native app | HA mobile app handles dashboard display |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCAF-01 | Template | **Done** |
| SCAF-02 | Template | **Done** |
| SCAF-03 | Template | **Done** |
| CONF-01 | Phase 1 | Pending |
| CONF-02 | Phase 1 | Pending |
| CONF-03 | Phase 1 | Pending |
| CONF-04 | Phase 1 | Pending |
| CONF-05 | Phase 1 | Pending |
| SENS-01 | Phase 2 | Pending |
| SENS-02 | Phase 2 | Pending |
| SENS-03 | Phase 2 | Pending |
| SENS-04 | Phase 1 | Pending |
| SRCH-01 | Phase 2 | Pending |
| SRCH-02 | Phase 2 | Pending |
| SRCH-03 | Phase 2 | Pending |
| SRCH-04 | Phase 2 | Pending |
| SRCH-05 | Phase 2 | Pending |
| REQT-01 | Phase 3 | Pending |
| REQT-02 | Phase 3 | Pending |
| REQT-03 | Phase 4 | Pending |
| REQT-04 | Phase 3 | Pending |
| REQT-05 | Phase 5 | Pending |
| CARD-01 | Phase 3 | Pending |
| CARD-02 | Phase 3 | Pending |
| CARD-03 | Phase 3 | Pending |
| CARD-04 | Phase 3 | Pending |
| CARD-05 | Phase 5 | Pending |
| DIST-01 | Template | **Done** |
| DIST-02 | Template | **Done** |
| DIST-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 30 total (was 31; TMDB config requirement removed)
- Satisfied by template: 6 (SCAF-01/02/03, DIST-01/02/03)
- Remaining: 24
- Mapped to phases: 30
- Unmapped: 0

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-23 — arr-lookup architecture, removed TMDB/MusicBrainz direct requirements*
