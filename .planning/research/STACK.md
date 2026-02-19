# Stack Research

**Domain:** Home Assistant HACS custom integration with embedded Lovelace card
**Researched:** 2026-02-19
**Confidence:** HIGH (Python/HA stack), MEDIUM (external API details verified via web search + official docs)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ (HA-bundled) | Integration backend | HA 2024.1+ ships Python 3.12; no choice, no installation needed |
| `aiohttp` | HA-bundled (~3.9.x) | All HTTP calls to TMDB, Radarr, Sonarr, Lidarr, MusicBrainz | Already in HA's virtualenv as a core dependency; adding it to `requirements` would install a second conflicting copy |
| `voluptuous` | HA-bundled | Config flow schema validation | Same as aiohttp — bundled, do not re-require |
| LitElement | HA-bundled (via shadow DOM) | Lovelace card UI | Extracted from HA's own `hui-masonry-view` or `hui-view` — the single-file no-build approach the scaffold already uses; avoids npm/webpack entirely |
| JavaScript (ES2020+) | No build step | Card logic | HA's built-in LitElement supports all modern JS; class fields, async/await, optional chaining all work in every supported browser |

### External APIs (No Python Libraries Needed)

All API communication is raw HTTP via `aiohttp.ClientSession`. No wrapper libraries are used — they would be pip dependencies that bloat the integration and diverge from HA conventions.

| API | Base URL | Auth | Notes |
|-----|----------|------|-------|
| TMDB v3 | `https://api.themoviedb.org/3` | `api_key` query param (or Bearer token) | Both auth methods active as of 2026; `api_key` is simpler for config-flow storage |
| TMDB Images | `https://image.tmdb.org/t/p/w92{poster_path}` | None | Width variants: w92, w154, w185, w342, w500, w780, original |
| Radarr v3 | `http://{host}:{port}/api/v3` | `X-Api-Key` header | POST `/movie/lookup?term=tmdb:{id}` then POST `/movie` |
| Sonarr v3 | `http://{host}:{port}/api/v3` | `X-Api-Key` header | GET `/series/lookup?term={title}` returns TVDB-backed data; POST `/series` requires tvdbId not tmdbId |
| Lidarr v1 | `http://{host}:{port}/api/v1` | `X-Api-Key` header | Note: Lidarr uses `/api/v1/` not `/api/v3/`; POST `/artist` requires `foreignArtistId` (MusicBrainz MBID) |
| MusicBrainz | `https://musicbrainz.org/ws/2` | None (free, no key) | Add `fmt=json` query param; requires `User-Agent` header; rate limit: 1 req/sec max |

### HA Integration Patterns (The "Framework")

These are not libraries to install — they are patterns imported from `homeassistant.*` packages that HA provides.

| Pattern | Import | Purpose | Why |
|---------|--------|---------|-----|
| `ConfigFlow` | `homeassistant.config_entries` | Multi-step setup UI | Required for HACS integrations; enables UI-only setup without YAML |
| `DataUpdateCoordinator` | `homeassistant.helpers.update_coordinator` | Polling interval + shared data | Single point of truth for all sensor data; prevents duplicate API calls across entities |
| `CoordinatorEntity` | `homeassistant.helpers.update_coordinator` | Entity linked to coordinator | Auto-handles coordinator state updates and availability |
| `SensorEntity` | `homeassistant.components.sensor` | Library count sensors | Existing scaffold pattern — keep it |
| `hass.services.async_register` | `homeassistant.core` | Register search/request actions | Card calls `this.hass.callService()` or `this.hass.callWS()` to trigger Python-side logic |
| `async_register_static_paths` | `homeassistant.components.http` | Serve the .js card file | The old `register_static_path` is deprecated (blocking I/O); removed in HA 2025.7; use `async_register_static_paths([StaticPathConfig(...)])` |
| `StaticPathConfig` | `homeassistant.components.http` | Path config dataclass | Required arg for `async_register_static_paths` |
| `runtime_data` on `ConfigEntry` | `homeassistant.config_entries` | Store coordinator on entry | Modern 2025 pattern replacing `hass.data[DOMAIN][entry.entry_id]`; passes hassfest quality scale checks |

### Supporting Libraries (None — Zero pip Dependencies)

The `requirements` array in `manifest.json` should remain empty (`[]`). Every capability needed is covered by:

1. `aiohttp` — already in HA virtualenv
2. Standard library (`asyncio`, `logging`, `pathlib`, `datetime`, `typing`)
3. HA framework imports

Adding pip requirements forces HACS to pip-install on user machines, risks version conflicts with HA's pinned deps, and adds update maintenance burden. The correct HA pattern is to use bundled libraries only.

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `hacs/action@main` | HACS structure validation | Already in `validate.yml`; checks hacs.json, manifest.json, file layout |
| `home-assistant/actions/hassfest@master` | HA integration validation | Already in `validate.yml`; checks manifest fields, config flow, quality scale rules |
| `softprops/action-gh-release@v2` | Release zip artifact | Already in `release.yml`; bumps manifest version from tag, zips custom_components |
| `jq` | Manifest version bump in CI | Used in release.yml; no additional install needed on ubuntu-latest |
| Browser DevTools | Card JS debugging | No build step = no source maps needed; F12 in HA frontend, direct source inspection |

## Installation

This project has no npm packages and no pip packages to install. Development setup:

```bash
# Python: HA dev environment (for local testing)
python -m venv venv
source venv/bin/activate
pip install homeassistant  # installs HA + all bundled deps for IDE type checking

# No JS dependencies — LitElement is extracted from HA at runtime
# No npm init, no package.json, no webpack, no rollup

# Validate locally (requires Docker)
docker run --rm -v "$(pwd)":/github/workspace \
  ghcr.io/home-assistant/hassfest:latest
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `aiohttp` (bundled) | `httpx`, `requests` | Never for HA integrations — they require pip deps; `requests` blocks the event loop |
| LitElement (HA-bundled) | Build toolchain (Vite + npm) | Only if card grows beyond ~1000 lines and needs TypeScript, component splitting, or tests; overkill for this project |
| `hass.callService()` from card | Direct REST API calls from JS | Never — bypasses HA auth, exposes API keys to browser, and breaks permission model |
| MusicBrainz (free, no key) | TMDB music search | TMDB does not index music; MusicBrainz is the correct source for Lidarr MBID lookup |
| `async_register_static_paths` | `register_static_path` (old) | Never — deprecated, removed in HA 2025.7; the scaffold uses the old method and must be updated |
| `runtime_data` pattern | `hass.data[DOMAIN][entry_id]` | Old pattern still works but fails quality scale; `runtime_data` is the 2025 standard |
| Raw dict for config schema | `voluptuous` (bundled) | voluptuous is the HA-standard approach for config flow validation; don't use pydantic (pip dep) |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `hass.http.register_static_path` | Deprecated; does blocking I/O in event loop; removed in HA 2025.7 | `await hass.http.async_register_static_paths([StaticPathConfig(...)])` |
| `hass.data[DOMAIN][entry_id]` to store coordinator | Old pattern; fails hassfest `runtime_data` quality scale rule | `entry.runtime_data = coordinator` in `async_setup_entry` |
| Any pip package for HTTP | Conflicts with HA's pinned aiohttp; adds dependency maintenance | `aiohttp.ClientSession` from HA's virtualenv |
| `api_key` in TMDB image URLs | Not needed; image CDN is public | Just use `https://image.tmdb.org/t/p/w{size}{poster_path}` with no key |
| tmdbId directly in Sonarr POST body | Sonarr v3 rejects it — requires tvdbId | Use `/api/v3/series/lookup?term={title}` first to get tvdbId, then POST |
| MusicBrainz without User-Agent header | Requests without User-Agent can be blocked by MusicBrainz servers | Set `User-Agent: ha-requestarr/{version} (github.com/Dabentz/ha-requestarr)` |
| Multiple aiohttp sessions per coordinator poll | Session creation has overhead; risks connection pool exhaustion | Create one session per `_async_update_data` call OR store a persistent session on the coordinator |
| `FRONTEND_SCRIPT_URL = f"/hacsfiles/{DOMAIN}/{DOMAIN}-card.js"` | HACS serves its own files from `/hacsfiles/`; serving from the integration's static path uses a different URL | Use `/requestarr/requestarr-card.js` as the registered static path, separate from HACS serving |

## Stack Patterns by Variant

**For adding a movie to Radarr (two-step API):**
- First: `GET /api/v3/movie/lookup?term=tmdb:{tmdb_id}` — returns full movie object with title, year, images
- Then: `POST /api/v3/movie` with body: `{tmdbId, title, qualityProfileId, rootFolderPath, monitored: true, addOptions: {searchForMovie: true}}`
- Both steps in one coordinator method, not two separate service calls

**For adding a series to Sonarr (three-step — TMDB → lookup → add):**
- TMDB search returns series title (not tvdbId)
- Sonarr lookup: `GET /api/v3/series/lookup?term={series_title}` — returns tvdbId in response
- Add: `POST /api/v3/series` with `{tvdbId, title, qualityProfileId, rootFolderPath, monitored: true, seasonFolder: true, addOptions: {searchForMissingEpisodes: false}}`
- This is the critical Sonarr difference vs Radarr

**For adding an artist to Lidarr (MusicBrainz → Lidarr):**
- MusicBrainz search: `GET https://musicbrainz.org/ws/2/artist?query={name}&fmt=json` — returns MBID
- Note Lidarr uses `/api/v1/` not `/api/v3/`
- Lidarr lookup: `GET /api/v1/artist/lookup?term={mbid}` optional — gets Lidarr's artist object
- Add: `POST /api/v1/artist` with `{foreignArtistId: mbid, artistName, qualityProfileId, metadataProfileId, rootFolderPath, monitored: true, addOptions: {monitor: "all", searchForMissingAlbums: false}}`

**For card-to-backend communication:**
- Register HA services in `async_setup_entry`: `requestarr.search`, `requestarr.request_movie`, `requestarr.request_series`, `requestarr.request_music`
- Card calls `this.hass.callService("requestarr", "search", {query, media_type})` — returns via state updates or `hass.callWS` for direct response
- Prefer service calls over WebSocket commands for actions; use sensor state for displaying results

## Version Compatibility

| Component | Compatible With | Notes |
|-----------|-----------------|-------|
| HA 2024.1.0+ | Python 3.12, aiohttp 3.9.x | `hacs.json` sets `homeassistant: "2024.1.0"` — reasonable minimum |
| `async_register_static_paths` | HA 2024.6+ | Introduced June 2024; old `register_static_path` removed in HA 2025.7 |
| `runtime_data` on ConfigEntry | HA 2024.x+ | Available in current HA; check exact minimum if supporting older installs |
| HACS action@main | Current HACS | `category: integration` for this repo type |
| hassfest@master | Rolling HA dev | Validates against current HA dev branch standards |
| Radarr API | v3 | Stable; use `/api/v3/` prefix for all endpoints |
| Sonarr API | v3 | Stable; use `/api/v3/` prefix for all endpoints |
| Lidarr API | v1 | Different from arr services: `/api/v1/` not `/api/v3/` |
| MusicBrainz API | Current (ws/2) | Stable for years; JSON via `fmt=json` |
| TMDB API | v3 | Both `api_key` query param and Bearer token work; no deprecation announced |

## Sources

- Home Assistant Developer Docs, async_register_static_paths blog (2024-06-18): https://developers.home-assistant.io/blog/2024/06/18/async_register_static_paths/ — MEDIUM confidence (official HA devblog, recent)
- Home Assistant Developer Docs, runtime_data quality scale rule: https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/runtime-data/ — HIGH confidence (official docs)
- Home Assistant Developer Docs, integration service actions: https://developers.home-assistant.io/docs/dev_101_services/ — HIGH confidence (official docs)
- HACS Plugin/Integration publishing docs: https://www.hacs.xyz/docs/publish/integration/ — HIGH confidence (official HACS docs)
- Radarr API Docs: https://radarr.video/docs/api/ — HIGH confidence (official, OpenAPI spec)
- Sonarr API Docs: https://sonarr.tv/docs/api/ — HIGH confidence (official)
- Lidarr API Docs: https://lidarr.audio/docs/api/ — HIGH confidence (official)
- MusicBrainz API Rate Limiting: https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting — HIGH confidence (official)
- MusicBrainz API Search: https://musicbrainz.org/doc/MusicBrainz_API/Search — HIGH confidence (official)
- TMDB API Getting Started: https://developer.themoviedb.org/docs/getting-started — HIGH confidence (official)
- Radarr GitHub issue #2320 (tmdb lookup workflow): https://github.com/Radarr/Radarr/issues/2320 — MEDIUM confidence (issue thread, multiple confirming replies)
- Sonarr GitHub issue #7565 (TMDB → TVDB ID requirement): https://github.com/Sonarr/Sonarr/issues/7565 — MEDIUM confidence (issue thread, confirmed behavior)
- Lidarr GitHub issue #578 (foreignArtistId / MusicBrainz): https://github.com/Lidarr/Lidarr/issues/578 — MEDIUM confidence (issue thread)
- WebSearch — HA deprecation of `register_static_path`, StaticPathConfig import path — MEDIUM confidence (multiple community corroborations)

---
*Stack research for: Home Assistant HACS media request integration (Requestarr)*
*Researched: 2026-02-19*
