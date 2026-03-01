---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: complete
last_updated: "2026-02-28T03:30:00.000Z"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 7
  completed_plans: 7
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-27)

**Core value:** Search for media and submit requests to arr stack from a single HA dashboard card — no separate app, no separate auth, no separate container
**Current focus:** v1 milestone complete. All 5 phases executed, verified, and tech debt resolved.

## Current Position

Phase: 5 of 5 (Library State + Card Polish + Validation) — COMPLETE
Plan: All plans complete
Status: v1 milestone complete — all tech debt resolved, audit passed 30/30
Last activity: 2026-02-28 — Tech debt fixed: show_* toggles wired, iot_class corrected, pytest CI added, binary_sensor removed

Progress: [████████████████████] 5/5 plans (100% of planned phases)

## What the Template Provides (Already Done)

The ha-hacs-template v1.0 overlay satisfies:

- **SCAF-01**: Modern `async_register_static_paths` + `StaticPathConfig` (HA 2025.7+)
- **SCAF-02**: Valid `manifest.json` with `iot_class: local_polling`, `version`, `dependencies: [frontend, http, websocket_api]`
- **SCAF-03**: `unique_id` pattern with `_abort_if_unique_id_configured()` (needs customization to use first arr URL)
- **DIST-01**: HACS-compatible structure (hacs.json, manifest.json, file layout)
- **DIST-02**: Frontend card served via async static path registration
- **DIST-03**: CI workflows (hassfest + hacs/action + pytest) in `.github/workflows/validate.yml`

## Accumulated Context

### Decisions

- [Init→Fixed]: iot_class corrected to `local_polling` (arr services are on LAN)
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
- [2026-02-27]: **Phase 3 executed** — request_movie + request_series WS commands, Lovelace card with Movies/TV tabs + confirm dialog
- [2026-02-27]: **send_result for all request errors** — never send_error, so JS sendMessagePromise always resolves (inline error display)
- [2026-02-27]: **HTTP 400 from arr add = already_exists** — Radarr/Sonarr reliably return 400 for duplicate adds
- [2026-02-27]: **int(quality_profile_id) cast** — options flow stores as string, arr services require int (422 without cast)
- [2026-02-27]: **Inline confirm dialog** — window.confirm blocked in shadow DOM; overlay div used instead
- [2026-02-27]: **Phase 4 executed** — request_artist WS command + Lidarr POST, Music tab activated with circular avatar rows
- [2026-02-28]: **Phase 5 executed** — in-library badge overlay (green pill on poster/avatar), disabled "In Library" button for owned items, full RequestarrCardEditor with service toggles and title field
- [2026-02-28]: **3-state model finalized** — `_getItemState` returns: requested, in_library, not_in_library (removed available/monitored)
- [2026-02-28]: **18-test suite complete** — conftest.py with HA 2025.1.4 shims, full coverage of config flow, coordinator, websocket, sensor, services
- [2026-02-28]: **CARD_VERSION 0.5.0** — final v1 card version
- [2026-02-28]: **Tech debt resolved** — show_* toggles wired to _renderTabs(), iot_class→local_polling, pytest CI job added, orphan binary_sensor.py removed, Phase 1 VERIFICATION.md created

### Deployment

Deploy to Fathom Docker LXC via scp (WSL2 → LXC at 192.168.50.110):

```bash
DOMAIN=requestarr DEST=root@192.168.50.110:/opt/homeassistant/config/custom_components/$DOMAIN && \
scp custom_components/$DOMAIN/*.py custom_components/$DOMAIN/*.json custom_components/$DOMAIN/*.yaml $DEST/ && \
scp custom_components/$DOMAIN/frontend/*-card.js $DEST/frontend/ && \
scp custom_components/$DOMAIN/translations/*.json $DEST/translations/
```

Note: `scp -r` nests directories instead of overwriting — use flat file copies above.

**First install:** full HA restart required (Settings → System → Restart)
**Subsequent deploys:** reload integration only (Settings → Devices & Services → Requestarr → ⋮ → Reload); card JS changes also require browser hard-refresh (Ctrl+Shift+R)

**E2E test checklist (manual UAT against live arr services):**
1. Settings → Devices & Services → Add Integration → Requestarr
2. Step 1: Enter Radarr URL + API key → validate → auto-advance
3. Step 2: Enter Sonarr URL + API key → validate → auto-advance
4. Step 3: Enter Lidarr URL + API key → validate → finish
5. Verify 3 sensors appear: radarr_status, sonarr_status, lidarr_status
6. Add Requestarr card to a dashboard
7. Search a movie → verify poster results → request one → confirm appears in Radarr
8. Search a TV show → request one → confirm appears in Sonarr
9. Search an artist → request one → confirm appears in Lidarr
10. Verify "In Library" green badge on already-owned items
11. Verify disabled "In Library" button (not re-requestable)
12. Open card editor → toggle show_movies/show_tv/show_music → verify tabs hide/show
13. Change card title → verify updates in card header

### Pending Todos

- Deploy via rsync to Fathom LXC (command above)
- Run E2E test checklist against live Radarr/Sonarr/Lidarr
- After UAT passes: run /gsd:complete-milestone v1.0 to archive

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-01
Stopped at: Post-v1 enhancements (seasons/albums, already_exists, nav bar redesign WIP). HA migrated from QNAP to Fathom LXC (192.168.50.110). SSH key auth established.
Resume file: None
Resume action: Finish nav bar redesign, deploy via rsync to Fathom LXC, run E2E checklist, then /gsd:complete-milestone v1.0
