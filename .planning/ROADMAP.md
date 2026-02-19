# Roadmap: Requestarr

## Overview

Requestarr delivers an HA-native media request card in 7 phases: fixing scaffold bugs, building the config flow and coordinator foundation, wiring sensors, implementing movie/TV search and request via WebSocket+TMDB, adding music search and Lidarr request, adding library state detection and notifications, and polishing for HACS submission. The build order is driven by hard dependencies: scaffold fixes gate everything, config flow gates the coordinator, coordinator gates sensors and search, search gates request submission.

## Phases

- [ ] **Phase 1: Scaffold Fixes** - Fix breaking HA 2025.7 deprecations and session leak
- [ ] **Phase 2: Config Flow + Coordinator** - Multi-step config wizard with live validation, coordinator with library polling
- [ ] **Phase 3: Sensors** - Library count sensors for Radarr, Sonarr, Lidarr
- [ ] **Phase 4: Movie & TV Search + Request** - TMDB search via WebSocket, Radarr/Sonarr request submission, card search UI
- [ ] **Phase 5: Music Search + Lidarr Request** - MusicBrainz search, Lidarr request, music tab in card
- [ ] **Phase 6: Library State + Card Polish** - "Already in library" detection, card editor, visual polish
- [ ] **Phase 7: HACS Distribution** - hassfest/HACS validation, reconfigure flow, distribution prep

## Phase Details

### Phase 1: Scaffold Fixes
**Goal**: Integration loads cleanly on HA 2025.7+ with no deprecation warnings or session leaks
**Depends on**: Nothing (first phase)
**Requirements**: SCAF-01, SCAF-02, SCAF-03, DIST-02
**Success Criteria** (what must be TRUE):
  1. Integration installs and loads without errors on HA 2025.7+
  2. No deprecation warnings in HA logs
  3. hassfest validation passes
  4. Card JS file is served at the registered static path
**Plans**: TBD

Plans:
- [ ] 01-01: Fix static path, aiohttp session, manifest, and unique_id

### Phase 2: Config Flow + Coordinator
**Goal**: User can set up the integration with live API validation for TMDB and all arr services; coordinator polls library counts
**Depends on**: Phase 1
**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, CONF-06
**Success Criteria** (what must be TRUE):
  1. Config flow validates TMDB API key with test search
  2. Config flow validates each arr service connection (optional skip)
  3. Quality profiles and root folders fetched and stored from each arr service
  4. Coordinator polls library counts every 5 minutes without errors
**Plans**: TBD

Plans:
- [ ] 02-01: Implement multi-step config flow with TMDB + arr validation
- [ ] 02-02: Implement DataUpdateCoordinator with library count polling

### Phase 3: Sensors
**Goal**: Library count sensors appear in HA and reflect real data from arr services
**Depends on**: Phase 2
**Requirements**: SENS-01, SENS-02, SENS-03, SENS-04
**Success Criteria** (what must be TRUE):
  1. Radarr movie count sensor shows correct value
  2. Sonarr series count sensor shows correct value
  3. Lidarr artist count sensor shows correct value
  4. Sensors update automatically every 5 minutes
**Plans**: TBD

Plans:
- [ ] 03-01: Implement CoordinatorEntity sensors for all three arr services

### Phase 4: Movie & TV Search + Request
**Goal**: Users can search for movies and TV shows from the card and submit requests to Radarr/Sonarr
**Depends on**: Phase 3
**Requirements**: SRCH-01, SRCH-02, SRCH-04, SRCH-05, REQT-01, REQT-02, REQT-04, CARD-01, CARD-02, CARD-03, CARD-04
**Success Criteria** (what must be TRUE):
  1. Card search returns TMDB results with posters, titles, years, and descriptions
  2. Movie request successfully adds to Radarr with correct quality profile
  3. TV request successfully adds to Sonarr (TMDB→TVDB ID translation works)
  4. Card shows tabbed interface with Movies and TV tabs
  5. TMDB API key never appears in card JavaScript or browser network requests
**Plans**: TBD

Plans:
- [ ] 04-01: Implement WebSocket search commands (TMDB movie + TV)
- [ ] 04-02: Implement Radarr movie request service
- [ ] 04-03: Implement Sonarr TV request service with TVDB translation
- [ ] 04-04: Build card search UI with results display and request buttons

### Phase 5: Music Search + Lidarr Request
**Goal**: Users can search for music artists and submit requests to Lidarr
**Depends on**: Phase 4
**Requirements**: SRCH-03, REQT-03
**Success Criteria** (what must be TRUE):
  1. MusicBrainz artist search returns results with correct User-Agent header
  2. Artist request successfully adds to Lidarr with foreignArtistId (MBID)
  3. Music tab in card works end-to-end (search → display → request)
**Plans**: TBD

Plans:
- [ ] 05-01: Implement MusicBrainz search + Lidarr request backend
- [ ] 05-02: Add music tab to card UI

### Phase 6: Library State + Card Polish
**Goal**: Card shows whether media is already in library; visual card editor works
**Depends on**: Phase 5
**Requirements**: REQT-05, CARD-05
**Success Criteria** (what must be TRUE):
  1. Search results show "In Library" badge for movies already in Radarr
  2. Search results show "In Library" badge for TV series already in Sonarr
  3. Search results show "In Library" badge for artists already in Lidarr
  4. Visual card editor allows configuration of all card settings
**Plans**: TBD

Plans:
- [ ] 06-01: Implement library state detection across all three services
- [ ] 06-02: Build visual card editor

### Phase 7: HACS Distribution
**Goal**: Integration is ready for public HACS distribution
**Depends on**: Phase 6
**Requirements**: DIST-01, DIST-03
**Success Criteria** (what must be TRUE):
  1. hassfest CI passes
  2. hacs/action CI passes
  3. Tagged release created on GitHub
  4. Integration installable via HACS custom repository
**Plans**: TBD

Plans:
- [ ] 07-01: HACS packaging, CI validation, and release prep

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Scaffold Fixes | 0/1 | Not started | - |
| 2. Config Flow + Coordinator | 0/2 | Not started | - |
| 3. Sensors | 0/1 | Not started | - |
| 4. Movie & TV Search + Request | 0/4 | Not started | - |
| 5. Music Search + Lidarr | 0/2 | Not started | - |
| 6. Library State + Card Polish | 0/2 | Not started | - |
| 7. HACS Distribution | 0/1 | Not started | - |
