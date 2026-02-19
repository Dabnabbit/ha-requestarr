# Requirements: Requestarr

**Defined:** 2026-02-19
**Core Value:** Users can search for media and submit requests to their arr stack from a single HA dashboard card — no separate app, no separate auth, no separate container.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Scaffold & Foundation

- [ ] **SCAF-01**: Integration loads on HA 2025.7+ without deprecation warnings (async static paths, shared aiohttp session)
- [ ] **SCAF-02**: `manifest.json` passes hassfest validation (correct `iot_class`, `version`, `unique_id` support)
- [ ] **SCAF-03**: Config entry has unique_id to prevent duplicate entries for same TMDB key

### Configuration

- [ ] **CONF-01**: User can configure TMDB API key with live validation (test search)
- [ ] **CONF-02**: User can configure Radarr connection (host, port, API key) with live validation
- [ ] **CONF-03**: User can configure Sonarr connection (host, port, API key) with live validation
- [ ] **CONF-04**: User can configure Lidarr connection (host, port, API key) with live validation
- [ ] **CONF-05**: Each arr service is optional (user can skip Radarr, Sonarr, or Lidarr)
- [ ] **CONF-06**: Quality profile and root folder fetched from each arr service at config time

### Sensors

- [ ] **SENS-01**: Radarr movie count sensor shows total movies in library
- [ ] **SENS-02**: Sonarr series count sensor shows total TV series in library
- [ ] **SENS-03**: Lidarr artist count sensor shows total artists in library
- [ ] **SENS-04**: Sensors update via DataUpdateCoordinator polling every 5 minutes

### Search

- [ ] **SRCH-01**: User can search for movies by title via WebSocket command
- [ ] **SRCH-02**: User can search for TV shows by title via WebSocket command
- [ ] **SRCH-03**: User can search for music artists via MusicBrainz WebSocket command
- [ ] **SRCH-04**: Search results display poster/thumbnail, title, year/date, and description
- [ ] **SRCH-05**: TMDB API key stays server-side (never exposed to card JavaScript)

### Requests

- [ ] **REQT-01**: User can request a movie to Radarr with one click
- [ ] **REQT-02**: User can request a TV series to Sonarr with one click (TMDB→TVDB translation handled)
- [ ] **REQT-03**: User can request a music artist to Lidarr with one click
- [ ] **REQT-04**: Request uses quality profile and root folder from config (not hardcoded)
- [ ] **REQT-05**: "Already in library" indicator shows when media is already in arr library

### Card UI

- [ ] **CARD-01**: Lovelace card with tabbed interface (Movies / TV / Music)
- [ ] **CARD-02**: Search input with submit button per tab
- [ ] **CARD-03**: Search results displayed as scrollable list with posters
- [ ] **CARD-04**: Request button on each result with visual feedback (Requested state)
- [ ] **CARD-05**: Visual card editor for configuration

### Distribution

- [ ] **DIST-01**: HACS-compatible (hacs.json, manifest.json, correct file structure)
- [ ] **DIST-02**: Frontend card served via integration's async static path registration
- [ ] **DIST-03**: CI passes hassfest and hacs/action validation

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Features

- **ENHC-01**: "Already requested" indicator with persistent state tracking
- **ENHC-02**: HA push notification when requested media becomes available
- **ENHC-03**: Per-tab search state persistence (switching tabs retains results)
- **ENHC-04**: Reconfigure flow to update credentials without removing integration

### Advanced

- **ADVN-01**: Season-level TV request granularity
- **ADVN-02**: 4K quality picker per-request
- **ADVN-03**: Trending/discover media browse
- **ADVN-04**: Request history and analytics
- **ADVN-05**: Per-user request quotas and approval workflow

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time search-as-you-type | TMDB rate limits, complexity, poor UX on slow connections |
| Multiple arr instance routing | Single instance per service is the target household model |
| Plex integration | Jellyfin-only household; use Overseerr for Plex |
| Jellyfin library display | Use Mediarr card; Requestarr stays request-focused |
| Now-playing / currently-streaming | Different feature; Mediarr covers this |
| Mobile-specific native app | HA mobile app handles dashboard display |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCAF-01 | Phase 1 | Pending |
| SCAF-02 | Phase 1 | Pending |
| SCAF-03 | Phase 1 | Pending |
| CONF-01 | Phase 2 | Pending |
| CONF-02 | Phase 2 | Pending |
| CONF-03 | Phase 2 | Pending |
| CONF-04 | Phase 2 | Pending |
| CONF-05 | Phase 2 | Pending |
| CONF-06 | Phase 2 | Pending |
| SENS-01 | Phase 3 | Pending |
| SENS-02 | Phase 3 | Pending |
| SENS-03 | Phase 3 | Pending |
| SENS-04 | Phase 3 | Pending |
| SRCH-01 | Phase 4 | Pending |
| SRCH-02 | Phase 4 | Pending |
| SRCH-03 | Phase 5 | Pending |
| SRCH-04 | Phase 4 | Pending |
| SRCH-05 | Phase 4 | Pending |
| REQT-01 | Phase 4 | Pending |
| REQT-02 | Phase 4 | Pending |
| REQT-03 | Phase 5 | Pending |
| REQT-04 | Phase 4 | Pending |
| REQT-05 | Phase 6 | Pending |
| CARD-01 | Phase 4 | Pending |
| CARD-02 | Phase 4 | Pending |
| CARD-03 | Phase 4 | Pending |
| CARD-04 | Phase 4 | Pending |
| CARD-05 | Phase 6 | Pending |
| DIST-01 | Phase 7 | Pending |
| DIST-02 | Phase 1 | Pending |
| DIST-03 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 after initial definition*
