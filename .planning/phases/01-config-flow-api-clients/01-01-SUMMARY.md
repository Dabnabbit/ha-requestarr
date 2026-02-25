---
phase: 01-config-flow-api-clients
plan: 01
subsystem: api, config
tags: [aiohttp, voluptuous, config-flow, coordinator, arr-api]

requires:
  - phase: template
    provides: scaffold with async_register_static_paths, runtime_data pattern, websocket/services setup
provides:
  - Uniform ArrClient class for all arr service API interactions
  - 3-step config flow wizard (Radarr -> Sonarr -> Lidarr) with live validation
  - RequestarrCoordinator polling library counts with partial failure tolerance
  - Options flow with profile/folder dropdowns and refresh button
  - Reconfigure flow re-running wizard with pre-filled values
affects: [sensors, search, request, coordinator]

tech-stack:
  added: []
  patterns: [uniform-arr-client, partial-failure-coordinator, skip-checkbox-config-flow]

key-files:
  created: []
  modified:
    - custom_components/requestarr/const.py
    - custom_components/requestarr/api.py
    - custom_components/requestarr/config_flow.py
    - custom_components/requestarr/coordinator.py
    - custom_components/requestarr/__init__.py
    - custom_components/requestarr/strings.json
    - custom_components/requestarr/translations/en.json

key-decisions:
  - "Single ArrClient class parameterized by service_type instead of separate client classes"
  - "Unique_id set to DOMAIN for singleton integration (one Requestarr per HA instance)"
  - "First quality profile and root folder used as defaults (arr services lack isDefault field)"
  - "Options flow dynamically shows only fields for configured services"
  - "Coordinator polls full library array for count (no lightweight count endpoint available)"

patterns-established:
  - "ArrClient pattern: base_url + /api/{version}/ + endpoint, X-Api-Key header, ssl parameter"
  - "Config flow step pattern: skip checkbox -> validate -> fetch profiles -> store -> advance"
  - "Partial failure coordinator: individual service errors don't fail the entire update"

requirements-completed: [CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, SENS-04]

duration: 15min
completed: 2026-02-25
---

# Phase 1: Config Flow + API Clients Summary

**Uniform ArrClient with 3-step config wizard (Radarr/Sonarr/Lidarr), live validation, profile fetching, and partial-failure coordinator polling library counts every 5 minutes**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-25
- **Completed:** 2026-02-25
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Uniform ArrClient handles Radarr (v3), Sonarr (v3), and Lidarr (v1) with automatic API version routing
- 3-step config flow validates connections live via /system/status and fetches profiles/folders
- Skip checkbox per step with "at least one required" enforcement on final step
- Coordinator polls library counts every 5 min with partial failure tolerance
- Options flow with dropdown profile/folder selection and refresh button
- Reconfigure flow re-runs wizard with current values pre-filled

## Task Commits

Each task was committed atomically:

1. **Task 1: Define constants and build uniform ArrClient** - `56396a6` (feat)
2. **Task 2: Build 3-step config flow with options and reconfigure** - `8107369` (feat)
3. **Task 3: Wire coordinator with partial failure tolerance** - `b630542` (feat)

## Files Created/Modified
- `custom_components/requestarr/const.py` - All CONF_ constants, API versions, library endpoints, service types
- `custom_components/requestarr/api.py` - Uniform ArrClient class for Radarr/Sonarr/Lidarr
- `custom_components/requestarr/config_flow.py` - 3-step wizard + options flow + reconfigure flow
- `custom_components/requestarr/coordinator.py` - RequestarrCoordinator with partial failure tolerance
- `custom_components/requestarr/__init__.py` - Updated to use RequestarrCoordinator
- `custom_components/requestarr/strings.json` - UI strings for all config flow steps
- `custom_components/requestarr/translations/en.json` - English translations (mirrors strings.json)

## Decisions Made
- Used single ArrClient class instead of separate RadarrClient/SonarrClient/LidarrClient — 95% code overlap
- Set unique_id to DOMAIN constant for singleton behavior (one Requestarr instance per HA)
- Used first profile/folder as default since arr services don't mark defaults
- Options flow schema is dynamically built — only shows fields for configured services
- Coordinator catches per-service errors individually; only raises UpdateFailed when all services fail

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ArrClient ready for search (async_search via lookup endpoints) and request (POST) in Phase 2+
- Coordinator has configured_services property for sensor entity creation in Phase 2
- Config entry stores all profile/folder data needed for request submission in Phase 3+
- All strings.json keys in sync with config_flow.py step IDs

---
*Phase: 01-config-flow-api-clients*
*Completed: 2026-02-25*
