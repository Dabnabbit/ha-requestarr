# Phase 2: Sensors + Search - Research

**Researched:** 2026-02-27
**Domain:** Home Assistant sensor entities + WebSocket command handlers for arr lookup API
**Confidence:** HIGH

## Summary

Phase 2 adds two capabilities to the existing Requestarr integration: (1) sensor entities that expose library counts and service status for each configured arr service, and (2) WebSocket command handlers that proxy search queries through arr lookup endpoints and return normalized results with public CDN image URLs.

The sensor implementation follows HA's `CoordinatorEntity` pattern, reusing the `RequestarrCoordinator` from Phase 1 which already polls library counts. Each sensor's state value is the service status (connected/disconnected/error) with the library count as an attribute. The WebSocket implementation registers three search commands (`requestarr/search_movies`, `requestarr/search_tv`, `requestarr/search_music`) that call the existing `ArrClient` with new lookup methods and return normalized payloads.

**Primary recommendation:** Add a `async_search` method to `ArrClient`, register three WebSocket commands with voluptuous schemas, and create conditional sensor entities per configured service -- all building on the Phase 1 foundation with no new dependencies.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Minimal fields per result: title, year, poster URL, full overview text (card truncates via CSS)
- Rewrite TMDB poster URLs from `/t/p/original/` to `/t/p/w300/` for card-sized thumbnails; TheTVDB and fanart.tv URLs passed through as-is
- Three separate WebSocket commands: `search_movies`, `search_tv`, `search_music` -- card calls the one matching its active tab
- Send full overview text; card handles truncation with CSS line-clamp
- Sensor state value = service status (connected / disconnected / error), not the library count
- Attributes: library count, service URL (masked/redacted), last successful sync time
- One sensor per configured service only: `sensor.requestarr_radarr`, `sensor.requestarr_sonarr`, `sensor.requestarr_lidarr`
- No combined/parent sensor
- Service-specific MDI icons: `mdi:movie` (Radarr), `mdi:television` (Sonarr), `mdi:music` (Lidarr)
- Structured error responses with distinct error codes: `service_not_configured`, `service_unavailable`, `invalid_query`
- Cap search results at 20 per query
- Reject empty search queries with error
- Include `in_library` boolean flag (derived from arr `id > 0`) in every search result
- Include `arr_id` (integer or null) for items already in library
- Always include external IDs: `tmdbId` (movies), `tvdbId` (TV), `foreignArtistId` (music)
- Include default quality profile name and root folder path in search results

### Claude's Discretion
- WebSocket command naming convention and registration pattern
- Exact sensor entity ID format and device info structure
- Error response JSON shape (as long as it includes error code + message)
- Coordinator update interval (currently 5 min from Phase 1)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SENS-01 | Radarr movie count sensor shows total movies in library | Coordinator already has `radarr_count`; sensor reads from coordinator data as attribute |
| SENS-02 | Sonarr series count sensor shows total TV series in library | Coordinator already has `sonarr_count`; sensor reads from coordinator data as attribute |
| SENS-03 | Lidarr artist count sensor shows total artists in library | Coordinator already has `lidarr_count`; sensor reads from coordinator data as attribute |
| SRCH-01 | Movie search via Radarr lookup endpoint through WebSocket | `ArrClient.async_search()` calls `/movie/lookup?term=X`; WS handler normalizes results |
| SRCH-02 | TV search via Sonarr lookup endpoint through WebSocket | `ArrClient.async_search()` calls `/series/lookup?term=X`; WS handler normalizes results |
| SRCH-03 | Music search via Lidarr lookup endpoint through WebSocket | `ArrClient.async_search()` calls `/artist/lookup?term=X`; WS handler normalizes results |
| SRCH-04 | Search results display poster/avatar thumbnail, title, year, description | Normalization extracts `remotePoster`/`remoteUrl`, rewrites TMDB to w300 |
| SRCH-05 | Arr API keys stay server-side; card uses public CDN image URLs | Use `remoteUrl`/`remotePoster` fields (public CDN); never expose arr base URL or API key |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| homeassistant.components.sensor | HA 2025.7+ | SensorEntity base class | Standard HA sensor platform |
| homeassistant.helpers.update_coordinator | HA 2025.7+ | CoordinatorEntity for efficient polling | Already used by Phase 1 coordinator |
| homeassistant.components.websocket_api | HA 2025.7+ | WebSocket command registration | Already used in Phase 1 template |
| voluptuous | bundled | WebSocket command schema validation | HA standard for input validation |
| aiohttp | bundled | HTTP client for arr API calls | Already used by ArrClient |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| homeassistant.helpers.device_registry | HA 2025.7+ | DeviceInfo for sensor grouping | Associate sensors under one Requestarr device |
| homeassistant.helpers.entity_platform | HA 2025.7+ | AddEntitiesCallback | Standard entity registration |

### Alternatives Considered
None -- HA's built-in sensor and websocket_api are the only correct choice for custom integrations.

## Architecture Patterns

### Recommended File Structure
```
custom_components/requestarr/
├── __init__.py          # Wire coordinator, forward platforms (already done)
├── api.py               # ArrClient with new async_search() method
├── const.py             # New lookup endpoint constants + WS type constants
├── coordinator.py       # Enhanced with last_successful_sync tracking
├── sensor.py            # 3 conditional sensors (one per configured service)
├── websocket.py         # 3 search commands + result normalization
├── config_flow.py       # Unchanged from Phase 1
├── services.py          # Unchanged from Phase 1
└── strings.json         # Sensor name translations
```

### Pattern 1: Conditional Sensor Creation
**What:** Only create sensors for services the user actually configured
**When to use:** When entity existence depends on config entry data

```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: RequestarrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[RequestarrSensor] = []

    for service_type in coordinator.configured_services:
        entities.append(
            RequestarrSensor(coordinator, entry, service_type)
        )
    async_add_entities(entities)
```

### Pattern 2: WebSocket Command with Entry Lookup
**What:** WebSocket handlers look up the config entry and its coordinator/clients
**When to use:** All WebSocket commands need access to integration data

```python
WS_TYPE_SEARCH_MOVIES = f"{DOMAIN}/search_movies"

@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_SEARCH_MOVIES,
        vol.Required("query"): str,
    }
)
@websocket_api.async_response
async def websocket_search_movies(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], "not_found", "No config entry")
        return
    coordinator = entries[0].runtime_data.coordinator
    # ... use coordinator to search
```

### Pattern 3: Result Normalization in Backend
**What:** Transform arr API responses into a uniform shape before sending to frontend
**When to use:** When different arr services return different field names

The backend normalizes all results into a consistent shape:
```python
{
    "title": str,          # movie title / series title / artist name
    "year": int | None,    # release year
    "overview": str,       # full text, card truncates via CSS
    "poster_url": str | None,  # public CDN URL (TMDB w300, TheTVDB, fanart.tv)
    "in_library": bool,    # True if arr id > 0
    "arr_id": int | None,  # arr internal ID if in library, None otherwise
    "tmdb_id": int | None, # for movies
    "tvdb_id": int | None, # for TV
    "foreign_artist_id": str | None,  # for music
    "quality_profile": str,    # default profile name from config
    "root_folder": str,        # default root folder path from config
}
```

### Pattern 4: Sensor State as Service Status
**What:** Use connected/disconnected/error as the state, library count as attribute
**When to use:** When the primary concern is service health, not a numeric value

```python
@property
def native_value(self) -> str | None:
    if self.coordinator.data is None:
        return None
    count = self.coordinator.data.get(f"{self._service_type}_count")
    errors = self.coordinator.data.get("errors", {})
    if self._service_type in errors:
        return "error"
    if count is None:
        return "disconnected"
    return "connected"

@property
def extra_state_attributes(self) -> dict[str, Any]:
    data = self.coordinator.data or {}
    count = data.get(f"{self._service_type}_count")
    return {
        "library_count": count,
        "service_url": self._masked_url,
        "last_successful_sync": self._last_successful_sync,
    }
```

### Anti-Patterns to Avoid
- **Exposing arr API keys in WebSocket responses:** Never include base URLs with auth in payloads sent to the card/browser
- **Using arr MediaCoverProxy URLs:** These require API key auth -- always use `remoteUrl`/`remotePoster` (public CDN)
- **Creating sensors for unconfigured services:** If user skipped Lidarr in config, no Lidarr sensor should exist
- **Returning unlimited results:** Arr lookups can return 50+ results; always cap at 20

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sensor entity lifecycle | Custom entity management | `CoordinatorEntity` base class | Handles updates, availability, removal automatically |
| WebSocket command registration | Manual JSON parsing | `@websocket_api.websocket_command` decorator | Type-safe, validated, follows HA patterns |
| Input validation | Manual string checking | `voluptuous` schemas | HA standard, consistent error messages |
| Image URL rewriting | Complex URL parser | Simple string replace on known TMDB pattern | Only one CDN needs rewriting (TMDB `/t/p/original/` to `/t/p/w300/`) |

**Key insight:** Phase 1 already built the hard parts (ArrClient, coordinator, config). Phase 2 is wiring -- connecting existing infrastructure to HA's sensor and WebSocket APIs.

## Common Pitfalls

### Pitfall 1: Sensor entity_id conflicts
**What goes wrong:** Multiple integrations using the same entity_id pattern causes conflicts
**Why it happens:** Not using `unique_id` properly, or using generic sensor names
**How to avoid:** Use `f"{entry.entry_id}_{service_type}"` as unique_id; HA auto-generates entity_id from domain + name
**Warning signs:** "Entity already exists" errors during setup

### Pitfall 2: WebSocket error response format
**What goes wrong:** Card can't parse error responses because they don't match expected format
**Why it happens:** Using `connection.send_error()` (returns HA standard error) vs `connection.send_result()` with error payload
**How to avoid:** For business errors (service not configured, empty query), send a result with an `error` field. Reserve `send_error()` for actual WebSocket protocol errors.
**Warning signs:** Card showing generic "Unknown error" instead of specific messages

### Pitfall 3: TMDB image URL size suffix
**What goes wrong:** Images load slowly because they're full-resolution originals
**Why it happens:** Using `remotePoster` as-is without rewriting the TMDB path
**How to avoid:** Replace `/t/p/original/` with `/t/p/w300/` for TMDB URLs only (TheTVDB and fanart.tv URLs are fine as-is)
**Warning signs:** Card images taking 2-5 seconds to load on first render

### Pitfall 4: Missing image handling
**What goes wrong:** Card shows broken image icons for artists without fanart.tv images
**Why it happens:** Many Lidarr artists (~40-60%) have no fanart.tv images, so `remotePoster` is null/empty
**How to avoid:** Return `poster_url: null` and let the card handle the placeholder (Phase 4/5 concern for display, but backend should handle null cleanly)
**Warning signs:** JavaScript errors from setting `img.src = null`

### Pitfall 5: Coordinator data not ready during search
**What goes wrong:** WebSocket search handler uses coordinator but coordinator hasn't done first refresh
**Why it happens:** WebSocket commands are registered in `async_setup()` (before any config entry loads), but search needs ArrClient from config entry
**How to avoid:** Search handlers must look up the config entry and its coordinator at call time, not at registration time. Check for missing entry gracefully.
**Warning signs:** `KeyError` or `AttributeError` when searching before integration is fully loaded

### Pitfall 6: Stale coordinator reference after reconfigure
**What goes wrong:** Options flow changes profiles/folders but search still uses old coordinator data
**Why it happens:** WebSocket handlers cache the coordinator reference
**How to avoid:** Always look up `hass.config_entries.async_entries(DOMAIN)[0].runtime_data.coordinator` fresh on each WS call
**Warning signs:** Search results showing old default profile after user changed it in options

## Code Examples

### ArrClient.async_search() Method

```python
async def async_search(self, query: str) -> list[dict[str, Any]]:
    """Search the arr service's lookup endpoint.

    Args:
        query: Search term.

    Returns:
        List of raw result dicts from the arr API.
    """
    endpoint = LOOKUP_ENDPOINTS[self._service_type]
    return await self._request("GET", endpoint, params={"term": query})
```

### Lookup Endpoint Constants

```python
# Lookup (search) endpoints per service
LOOKUP_ENDPOINTS: dict[str, str] = {
    SERVICE_RADARR: "/movie/lookup",
    SERVICE_SONARR: "/series/lookup",
    SERVICE_LIDARR: "/artist/lookup",
}
```

### Result Normalization

```python
def _normalize_movie_result(item: dict, config_data: dict) -> dict:
    poster_url = item.get("remotePoster")
    if not poster_url:
        for img in item.get("images", []):
            if img.get("coverType") == "poster":
                poster_url = img.get("remoteUrl")
                break

    # Rewrite TMDB to w300
    if poster_url and "image.tmdb.org/t/p/original" in poster_url:
        poster_url = poster_url.replace("/t/p/original/", "/t/p/w300/")

    arr_id = item.get("id", 0)
    return {
        "title": item.get("title", ""),
        "year": item.get("year"),
        "overview": item.get("overview", ""),
        "poster_url": poster_url,
        "in_library": arr_id > 0,
        "arr_id": arr_id if arr_id > 0 else None,
        "tmdb_id": item.get("tmdbId"),
        "quality_profile": config_data.get("radarr_profiles", [{}])[0].get("name", ""),
        "root_folder": config_data.get(CONF_RADARR_ROOT_FOLDER, ""),
    }
```

### WebSocket Error Response Pattern

```python
# Business error (service not configured, bad query) -- use send_result with error field
connection.send_result(msg["id"], {
    "error": "service_not_configured",
    "message": "Radarr is not configured in Requestarr",
    "results": [],
})

# Protocol error (no config entry at all) -- use send_error
connection.send_error(msg["id"], "not_found", "Requestarr integration not configured")
```

### Sensor with Conditional Creation and Status State

```python
SERVICE_SENSOR_CONFIG = {
    SERVICE_RADARR: {
        "name": "Radarr",
        "icon": "mdi:movie",
        "url_key": CONF_RADARR_URL,
    },
    SERVICE_SONARR: {
        "name": "Sonarr",
        "icon": "mdi:television",
        "url_key": CONF_SONARR_URL,
    },
    SERVICE_LIDARR: {
        "name": "Lidarr",
        "icon": "mdi:music",
        "url_key": CONF_LIDARR_URL,
    },
}
```

### Coordinator Enhancement for Last Sync Tracking

```python
# In _async_update_data, track last successful sync per service
for service_type, client in self._clients.items():
    try:
        count = await client.async_get_library_count()
        data[f"{service_type}_count"] = count
        data[f"{service_type}_last_sync"] = dt_util.utcnow().isoformat()
    except (CannotConnectError, InvalidAuthError) as err:
        # Keep previous last_sync value on error
        if self.data:
            data[f"{service_type}_last_sync"] = self.data.get(
                f"{service_type}_last_sync"
            )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Entity` base class | `CoordinatorEntity` | HA 2021.12+ | Automatic coordinator subscription, no manual listener management |
| `platform_schema` | `config_entry_only` | HA 2022+ | No YAML config, config flow only |
| `async_setup_platform` | `async_setup_entry` | HA 2021+ | Config entry-based platform setup |
| Generic websocket handler | `@websocket_api.websocket_command` decorator | HA 2022+ | Type-safe, auto-validated |
| `websocket_api.result_message` | `connection.send_result` | HA 2023+ | Direct connection method preferred |

**Deprecated/outdated:**
- `Entity` without coordinator: Use `CoordinatorEntity` for any polling integration
- `platform_schema` in sensor.py: Config entry-only integrations should not have YAML platform config
- `TemplateCoordinator` / `TemplateSensor`: Template placeholders from scaffold that must be replaced

## Open Questions

1. **Quality profile name resolution**
   - What we know: Config stores `radarr_quality_profile_id` (integer) and `radarr_profiles` (list of {id, name} dicts)
   - What's unclear: Whether to look up profile name from the stored list or include it directly
   - Recommendation: Look up from stored profiles list -- it's already in config entry data. Match by current `quality_profile_id` to get the name.

2. **Lidarr lookup endpoint choice**
   - What we know: Lidarr has `/artist/lookup` (artists only) and `/search` (mixed artists + albums)
   - What's unclear: Which to use for the `search_music` command
   - Recommendation: Use `/artist/lookup` for Phase 2 (CONTEXT.md says "search_music"). Album search is deferred to v2 (ENHC-05). This keeps the payload consistent with the other two commands.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `api.py`, `coordinator.py`, `const.py`, `__init__.py`, `websocket.py`, `sensor.py` -- Phase 1 implementation
- `.planning/research/ARR_LOOKUP_API.md` -- Comprehensive arr lookup endpoint research (2026-02-23)
- `.planning/research/ARCHITECTURE.md` -- HA integration architecture patterns

### Secondary (MEDIUM confidence)
- Home Assistant developer docs: sensor platform, websocket_api, CoordinatorEntity patterns
- `.planning/phases/02-sensors-search/02-CONTEXT.md` -- User design decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - HA built-in APIs only, no third-party dependencies
- Architecture: HIGH - follows established HA patterns, extends existing Phase 1 code
- Pitfalls: HIGH - identified from real codebase analysis and arr API behavior

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (stable HA APIs, unlikely to change)
