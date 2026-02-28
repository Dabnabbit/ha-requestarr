---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-02-28T02:12:20.931Z"
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 5
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-23)

**Core value:** Search for media and submit requests to arr stack from a single HA dashboard card — no separate app, no separate auth, no separate container
**Current focus:** Phase 2 complete. Ready for Phase 3.

## Current Position

Phase: 3 of 5 (Movie & TV Request)
Plan: 0 of 2 in current phase
Status: Phase 2 complete, ready to plan Phase 3
Last activity: 2026-02-27 — Phase 2 executed: service status sensors, WebSocket search commands with result normalization

Progress: [█████░░░░░] 50% (Phase 2 complete)

## What the Template Provides (Already Done)

The ha-hacs-template v1.0 overlay satisfies:

- **SCAF-01**: Modern `async_register_static_paths` + `StaticPathConfig` (HA 2025.7+)
- **SCAF-02**: Valid `manifest.json` with `iot_class: cloud_polling`, `version`, `dependencies: [frontend, http, websocket_api]`
- **SCAF-03**: `unique_id` pattern with `_abort_if_unique_id_configured()` (needs customization to use first arr URL)
- **DIST-01**: HACS-compatible structure (hacs.json, manifest.json, file layout)
- **DIST-02**: Frontend card served via async static path registration
- **DIST-03**: CI workflows (hassfest + hacs/action) in `.github/workflows/validate.yml`

## Accumulated Context

### Decisions

- [Init]: iot_class is `cloud_polling` (arr services may be remote)
- [Init]: WebSocket commands for search (returns data to card)
- [Init]: Service calls for request submission (fire-and-forget with status)
- [Init]: Quality profiles + root folders fetched at config time, not hardcoded
- [Template]: Re-scaffolded from ha-hacs-template v1.0 (2026-02-20)
- [2026-02-23]: **Arr lookup endpoints replace TMDB + MusicBrainz direct calls** — eliminates TMDB key, MusicBrainz client, TVDB ID mapping; uniform X-Api-Key auth; richer metadata
- [2026-02-23]: **Config flow is 3 steps** (Radarr → Sonarr → Lidarr), not 4 — no TMDB step
- [2026-02-23]: **Image URLs from `remoteUrl`/`remotePoster`** fields in arr responses — public CDN URLs (TMDB, TheTVDB, fanart.tv), no auth needed for `<img>` tags
- [2026-02-23]: **"In library" detection** via `id > 0` in arr lookup response — no separate check
- [2026-02-23]: **Sonarr tvdbId** already in lookup response — no TMDB external_ids call needed
- [2026-02-23]: **Lidarr uses /api/v1/** not /api/v3/ — different from Radarr/Sonarr
- [2026-02-23]: **Lidarr needs metadataProfileId** in addition to qualityProfileId — fetch at config time
- [2026-02-23]: **Circular avatars for music** results (Spotify/Apple Music convention) — handles missing fanart.tv images with initials placeholder
- [2026-02-23]: **Jellyseerr UX patterns adopted**: 300ms debounce, green/blue/yellow/red status badges, poster-centric results, 3-tap request flow
- [2026-02-23]: **Jellyseerr patterns avoided**: full-page navigation, discover/trending, advanced requester options, granular permissions, infinite scroll, season selection table

### Research Documents

- `.planning/research/STACK.md` — Technology stack research
- `.planning/research/FEATURES.md` — Feature landscape and prioritization
- `.planning/research/ARCHITECTURE.md` — HA integration architecture patterns
- `.planning/research/PITFALLS.md` — Known pitfalls and prevention
- `.planning/research/SUMMARY.md` — Research synthesis
- `.planning/research/JELLYSEERR_UX.md` — Jellyseerr UI/UX analysis (2026-02-23)
- `.planning/research/MUSIC_UX.md` — Music tab UX research: Lidarr, Ombi, MusicBrainz, streaming apps (2026-02-23)
- `.planning/research/ARR_LOOKUP_API.md` — Arr lookup API as primary search source (2026-02-23)

- [2026-02-25]: **Phase 1 executed** — single ArrClient class for all arr services, parameterized by service_type
- [2026-02-25]: **Unique_id = DOMAIN** — singleton integration, one Requestarr per HA instance
- [2026-02-25]: **First profile/folder used as default** — arr services don't have isDefault field
- [2026-02-25]: **Options flow dynamic schema** — only shows fields for configured services
- [2026-02-25]: **Partial failure coordinator** — individual service errors don't fail entire update
- [2026-02-27]: **Phase 2 executed** — conditional service status sensors, three WebSocket search commands
- [2026-02-27]: **Sensor state = service status** — connected/disconnected/error with library_count as attribute
- [2026-02-27]: **Search result normalization** — backend extracts remotePoster, rewrites TMDB to w300, passes TheTVDB/fanart.tv through
- [2026-02-27]: **Structured WS error codes** — invalid_query, service_not_configured, service_unavailable
- [2026-02-27]: **Search results self-contained** — include in_library, arr_id, external IDs, default profile name, root folder path
- [2026-02-27]: **Profile name resolution** — stored profiles list matched by current quality_profile_id

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-27
Stopped at: Phase 2 complete, verification pending
Resume file: .planning/phases/02-sensors-search/02-01-SUMMARY.md
Resume action: Run /gsd:plan-phase 3 for Movie & TV Request
