# Requestarr

## What This Is

A Home Assistant HACS integration that lets household members search for and request movies, TV shows, and music directly from a Lovelace dashboard card. It connects to TMDB for search and Radarr/Sonarr/Lidarr for fulfillment, replacing the need for a separate Jellyseerr container.

## Core Value

Users can search for media and submit requests to their arr stack from a single HA dashboard card — no separate app, no separate auth, no separate container.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Multi-step config flow: TMDB API key → Radarr (optional) → Sonarr (optional) → Lidarr (optional)
- [ ] Connection validation for each service during config
- [ ] TMDB search for movies, TV shows, and multi-search
- [ ] Search results displayed with poster thumbnails, titles, years, and descriptions
- [ ] One-click request to send movie to Radarr
- [ ] One-click request to send TV series to Sonarr
- [ ] Music search (MusicBrainz or TMDB) with request to Lidarr
- [ ] Tabbed card UI: Movies / TV / Music
- [ ] Library count sensors: Radarr movies, Sonarr series, Lidarr artists
- [ ] Request status tracking: requested → downloading → available
- [ ] "Already in library" / "already requested" state detection
- [ ] Lovelace card with visual editor
- [ ] HACS-compatible distribution (hacs.json, manifest.json, GitHub Actions)
- [ ] Frontend card served via integration's static path registration
- [ ] Per-user request context via HA user identity

### Out of Scope

- Now-playing / currently-streaming display — deferred to v2 (absorb Mediarr features)
- Upcoming releases calendar — deferred to v2
- Recently added media — deferred to v2
- Per-user quotas and approval workflows — deferred to v3
- Python backend for state persistence — deferred to v3
- Request history and analytics — deferred to v3
- Mobile-specific native app — HA mobile app handles this
- Plex integration — Jellyfin-only household

## Context

- **Homelab**: QNAP TS-464 running all services via Portainer stacks
- **Existing stack**: Radarr (7878), Sonarr (8989), Lidarr (8686), all on 192.168.50.250
- **Current request UI**: Jellyseerr — works but is a separate container with separate auth; lacks Lidarr/music support
- **HACS template**: Re-scaffolded from ha-hacs-template v1.0 via `copier copy` (2026-02-20). Template provides correct HA 2025.7+ patterns, CI, tests, multi-step config flow, WebSocket framework, and service registration. All files need Requestarr-specific customization.
- **Copier answers**: `.copier-answers.yml` tracks template version (v1.0) and variables; `copier update` pulls future template improvements
- **Target users**: Household members (family) who use HA app on phones/tablets/TVs
- **Arr API version**: v3 for all three services (Radarr, Sonarr, Lidarr)
- **TMDB**: Free API key, well-documented REST API, poster images via image.tmdb.org
- **Music search**: MusicBrainz is free and doesn't require API key; TMDB doesn't cover music
- **HA integration patterns**: ConfigFlow, DataUpdateCoordinator, CoordinatorEntity, register_static_path for frontend

## Constraints

- **Tech stack**: Python (HA integration) + JavaScript/LitElement (Lovelace card) — no build tooling, single JS file
- **HACS compliance**: Must pass hacs/action and hassfest validation
- **No external dependencies**: All API calls via aiohttp (already in HA), no pip requirements needed
- **Card size**: Single JS file, no npm/webpack — LitElement from HA's built-in instance
- **API auth**: Arr services use X-Api-Key header; TMDB uses api_key query parameter
- **Network**: All services on same LAN (192.168.50.250), no need for SSL/external access

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Replace Jellyseerr with native HA card | Eliminate separate container + auth, add Lidarr support from day one | — Pending |
| TMDB for movie/TV search | Free, well-documented, poster images included | — Pending |
| MusicBrainz for music search | Free, no API key needed, comprehensive music database | — Pending |
| Single JS file (no build step) | HACS convention, simpler distribution, LitElement from HA | — Pending |
| Tabbed card UI (Movies/TV/Music) | Natural organization matching arr service boundaries | — Pending |

---
*Last updated: 2026-02-20 after template overlay from ha-hacs-template v1.0*
