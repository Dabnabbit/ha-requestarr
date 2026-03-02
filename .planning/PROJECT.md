# Requestarr

## What This Is

A Home Assistant HACS integration that lets household members search for and request movies, TV shows, and music directly from a Lovelace dashboard card. It connects to Radarr/Sonarr/Lidarr for search and fulfillment (arr lookup endpoints as primary search API — no TMDB key needed), replacing the need for a separate Jellyseerr container.

## Core Value

Users can search for media and submit requests to their arr stack from a single HA dashboard card — no separate app, no separate auth, no separate container.

## Requirements

### Validated

- ✓ Multi-step config flow: Radarr (optional) → Sonarr (optional) → Lidarr (optional) with live validation — Phase 1
- ✓ Connection validation for each arr service during config, fetching quality profiles + root folders — Phase 1
- ✓ Library count sensors: Radarr movies, Sonarr series, Lidarr artists — Phase 2
- ✓ Movie search via Radarr lookup API (returns TMDB metadata + poster CDN URLs) — Phase 2
- ✓ TV search via Sonarr lookup API (returns TheTVDB metadata + poster CDN URLs + tvdbId) — Phase 2
- ✓ Music search via Lidarr lookup API (returns fanart.tv images + MusicBrainz metadata) — Phase 4
- ✓ Search results displayed with poster/avatar thumbnails, titles, years — Phase 2/3
- ✓ One-click request to send movie to Radarr — Phase 3
- ✓ One-click request to send TV series to Sonarr (tvdbId from lookup, no TMDB translation) — Phase 3
- ✓ One-click request to send artist to Lidarr (foreignArtistId from lookup) — Phase 4
- ✓ Tabbed card UI: Movies / TV / Music — Phase 3 (Movies/TV), Phase 4 (Music activated)
- ✓ Frontend card served via integration's static path registration — Phase 1 (template)

### Active

- [ ] "Already in library" detection via arr lookup response (id > 0) with visual badge — Phase 5 (REQT-05)
- [ ] Lovelace card with visual editor — Phase 5 (CARD-05)
- [ ] HACS-compatible distribution validation (hassfest + hacs/action CI) — Phase 5
- [ ] Per-user request context via HA user identity — Phase 5 (deferred if complexity high)

### v2 — Series Lifecycle + Display Features

- [ ] **Series lifecycle: Archive** — delete files from disk but keep entry in Sonarr/Radarr (unmonitored). Frees real disk space. Sonarr: `DELETE /api/v3/episodefile/{id}` per file + set series `monitored: false`, store per-season monitored state for later restore. Radarr: `DELETE /api/v3/moviefile/{id}` + `monitored: false`.
- [ ] **Series lifecycle: Load/Re-request** — re-monitor an archived series and trigger search to re-download. Must handle indexer rate limiting gracefully (stagger season searches, show progress, don't hammer all at once). Only re-monitor seasons that were monitored before archiving (preserve user's existing monitoring choices). Sonarr: restore per-season monitored state, then `POST /api/v3/command` with `SeriesSearch`.
- [ ] **Library state display** — show series/movie status in card: "On disk" (has files), "Archived" (in arr but no files, unmonitored), "Downloading" (in queue), "Missing" (monitored but no files)
- [ ] **Archive confirmation** — "Are you sure? This will delete X GB of files" with size info from arr API (`sizeOnDisk` from series/movie endpoint)
- [ ] **Disk space indicator** — show root folder free space so users know capacity before loading series
- [ ] Now-playing / currently-streaming display (absorb Mediarr features)
- [ ] Upcoming releases calendar
- [ ] Recently added media
- [ ] Album-level music requests (v1 uses artist-level "monitor all")
- [ ] Season-level TV request granularity (v1 requests full series)

### Out of Scope

- Discover/trending browse — deferred (Jellyseerr has this but it's high complexity)
- Per-user quotas and approval workflows — deferred to v3
- Python backend for state persistence — deferred to v3
- Request history and analytics — deferred to v3
- Cold storage archive — compress + move to external/slow drive instead of deleting; restore from local before falling back to re-download. Requires hardware (external drive on QNAP). Revisit if/when cold storage is available.
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
| Replace Jellyseerr with native HA card | Eliminate separate container + auth, add Lidarr support from day one | Shipped Phase 1-4 |
| Arr lookup endpoints for all search | Eliminates TMDB key, MusicBrainz client, TVDB mapping; uniform X-Api-Key auth; richer metadata (multi-source ratings); free "in library" detection (id > 0) | Decided 2026-02-23, validated Phase 2-4 |
| Public CDN URLs for images | Arr responses include `remoteUrl`/`remotePoster` pointing to public CDNs (TMDB, TheTVDB, fanart.tv) — no auth needed for `<img>` tags | Decided 2026-02-23, validated Phase 2-4 |
| Circular avatars for music results | Spotify/Apple Music convention — circle = artist, rectangle = album/content; handles 40-60% missing fanart.tv images with initials placeholder | Shipped Phase 4 |
| Single JS file (no build step) | HACS convention, simpler distribution, LitElement from HA | Shipped Phase 3 (515 lines) |
| Tabbed card UI (Movies/TV/Music) | Natural organization matching arr service boundaries | Shipped Phase 3 (Movies/TV), Phase 4 (Music) |
| Jellyseerr UX patterns as design reference | 300ms debounce, green/blue/yellow/red status badges, poster-centric results, 3-tap request flow | Decided 2026-02-23, implemented Phase 3 |
| `send_result` for all request errors (not `send_error`) | JS `sendMessagePromise` always resolves; card can display inline errors without try/catch at top level | Phase 3 — validated pattern |
| HTTP 400 from arr add endpoint = duplicate | Radarr/Sonarr reliably return 400 for duplicate adds — mapped to `already_exists` error code | Phase 3 |
| `int(quality_profile_id)` cast in POST payloads | Options flow stores profile IDs as strings from HTML selectors; arr services validate as integers (422 without cast) | Phase 3 |
| Inline confirm dialog (not `window.confirm`) | `window.confirm` is blocked in shadow DOM contexts; inline overlay required | Phase 3 |

---
*Last updated: 2026-02-27 after Phase 3 — movie/TV request + Lovelace card shipped; Phase 4 (Music/Lidarr) also complete*
