# Requestarr

## What This Is

A Home Assistant HACS integration that lets household members search for and request movies, TV shows, and music directly from a Lovelace dashboard card. It connects to TMDB for search and Radarr/Sonarr/Lidarr for fulfillment, replacing the need for a separate Jellyseerr container.

## Core Value

Users can search for media and submit requests to their arr stack from a single HA dashboard card — no separate app, no separate auth, no separate container.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Multi-step config flow: Radarr (optional) → Sonarr (optional) → Lidarr (optional) with live validation
- [ ] Connection validation for each arr service during config, fetching quality profiles + root folders
- [ ] Movie search via Radarr lookup API (returns TMDB metadata + poster CDN URLs)
- [ ] TV search via Sonarr lookup API (returns TheTVDB metadata + poster CDN URLs + tvdbId)
- [ ] Music search via Lidarr lookup API (returns fanart.tv images + MusicBrainz metadata)
- [ ] Search results displayed with poster/avatar thumbnails, titles, years, and descriptions
- [ ] One-click request to send movie to Radarr
- [ ] One-click request to send TV series to Sonarr (tvdbId already in lookup response)
- [ ] One-click request to send artist to Lidarr (foreignArtistId from lookup)
- [ ] Tabbed card UI: Movies / TV / Music
- [ ] Library count sensors: Radarr movies, Sonarr series, Lidarr artists
- [ ] "Already in library" detection via arr lookup response (id > 0)
- [ ] Lovelace card with visual editor
- [ ] HACS-compatible distribution (hacs.json, manifest.json, GitHub Actions)
- [ ] Frontend card served via integration's static path registration
- [ ] Per-user request context via HA user identity

### Out of Scope

- Now-playing / currently-streaming display — deferred to v2 (absorb Mediarr features)
- Upcoming releases calendar — deferred to v2
- Recently added media — deferred to v2
- Discover/trending browse — deferred to v2 (Jellyseerr has this but it's high complexity)
- Album-level music requests — deferred to v2 (v1 uses artist-level "monitor all")
- Per-user quotas and approval workflows — deferred to v3
- Python backend for state persistence — deferred to v3
- Request history and analytics — deferred to v3
- Season-level TV request granularity — deferred to v2 (v1 requests full series)
- Mobile-specific native app — HA mobile app handles this
- Plex integration — Jellyfin-only household
- Direct TMDB/MusicBrainz API calls — arr lookup endpoints provide superset of needed data

## Context

- **Homelab**: QNAP TS-464 running all services via Portainer stacks
- **Existing stack**: Radarr (7878), Sonarr (8989), Lidarr (8686), all on 192.168.50.250
- **Current request UI**: Jellyseerr — works but is a separate container with separate auth; lacks Lidarr/music support
- **HACS template**: Re-scaffolded from ha-hacs-template v1.0 via `copier copy` (2026-02-20). Template provides correct HA 2025.7+ patterns, CI, tests, multi-step config flow, WebSocket framework, and service registration. All files need Requestarr-specific customization.
- **Copier answers**: `.copier-answers.yml` tracks template version (v1.0) and variables; `copier update` pulls future template improvements
- **Target users**: Household members (family) who use HA app on phones/tablets/TVs
- **Arr API version**: Radarr v3, Sonarr v3, Lidarr v1 (not v3!)
- **Search architecture**: Arr lookup endpoints are the primary search API — no TMDB key or MusicBrainz client needed. Each arr service proxies upstream metadata (TMDB, TheTVDB, MusicBrainz/fanart.tv) and returns rich results including public CDN image URLs.
- **Image strategy**: Use `remoteUrl`/`remotePoster` fields from arr lookup responses — these point to public CDNs (image.tmdb.org, artworks.thetvdb.com, assets.fanart.tv) requiring no auth. Rewrite TMDB URLs from `/t/p/original/` to `/t/p/w342/` for card performance.
- **HA integration patterns**: ConfigFlow, DataUpdateCoordinator, CoordinatorEntity, register_static_path for frontend

## Constraints

- **Tech stack**: Python (HA integration) + JavaScript/LitElement (Lovelace card) — no build tooling, single JS file
- **HACS compliance**: Must pass hacs/action and hassfest validation
- **No external dependencies**: All API calls via aiohttp (already in HA), no pip requirements needed
- **Card size**: Single JS file, no npm/webpack — LitElement from HA's built-in instance
- **API auth**: All arr services use uniform X-Api-Key header pattern — no TMDB key, no MusicBrainz User-Agent needed
- **Network**: All services on same LAN (192.168.50.250), no need for SSL/external access

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Replace Jellyseerr with native HA card | Eliminate separate container + auth, add Lidarr support from day one | — Pending |
| Arr lookup endpoints for all search | Eliminates TMDB key, MusicBrainz client, TVDB mapping; uniform X-Api-Key auth; richer metadata (multi-source ratings); free "in library" detection (id > 0) | Decided 2026-02-23 |
| Public CDN URLs for images | Arr responses include `remoteUrl`/`remotePoster` pointing to public CDNs (TMDB, TheTVDB, fanart.tv) — no auth needed for `<img>` tags | Decided 2026-02-23 |
| Circular avatars for music results | Spotify/Apple Music convention — circle = artist, rectangle = album/content; handles 40-60% missing fanart.tv images with initials placeholder | Decided 2026-02-23 |
| Single JS file (no build step) | HACS convention, simpler distribution, LitElement from HA | — Pending |
| Tabbed card UI (Movies/TV/Music) | Natural organization matching arr service boundaries | — Pending |
| Jellyseerr UX patterns as design reference | 300ms debounce, green/blue/yellow/red status badges, poster-centric results, 3-tap request flow, auto-approval defaults | Decided 2026-02-23 |

---
*Last updated: 2026-02-23 — arr-lookup architecture, Jellyseerr UX research, music UX research*
