# Architecture Research

**Domain:** Home Assistant HACS integration — media request management
**Researched:** 2026-02-19
**Confidence:** HIGH (patterns verified against HA developer docs and existing scaffold)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser / HA Frontend                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              requestarr-card (LitElement)                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │   │
│  │  │ Movies   │  │ TV Shows │  │  Music   │  (tab state)  │   │
│  │  │   Tab    │  │   Tab    │  │   Tab    │               │   │
│  │  └──────────┘  └──────────┘  └──────────┘               │   │
│  │       ↑ hass.states (sensor entities for library counts)  │   │
│  │       ↓ hass.connection.sendMessagePromise (search/req)   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
              │                                  │
        WebSocket API                      Static file path
              │                          /hacsfiles/requestarr/
              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Home Assistant Core                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              requestarr integration (__init__.py)         │   │
│  │                                                           │   │
│  │  ┌─────────────────────┐   ┌──────────────────────────┐  │   │
│  │  │  RequestarrCoord-   │   │  WebSocket Commands       │  │   │
│  │  │  inator             │   │                           │  │   │
│  │  │  (poll loop)        │   │  requestarr/search        │  │   │
│  │  │  - library counts   │   │  requestarr/request_media │  │   │
│  │  └──────────┬──────────┘   └──────────────────────────┘  │   │
│  │             │                         │                    │   │
│  │  ┌──────────▼──────────┐              │                    │   │
│  │  │  Sensor Entities    │              │                    │   │
│  │  │  - radarr_movies    │              │                    │   │
│  │  │  - sonarr_series    │              │                    │   │
│  │  │  - lidarr_artists   │              │                    │   │
│  │  └─────────────────────┘              │                    │   │
│  └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
              │                                  │
              ↓ aiohttp                          ↓ aiohttp
┌─────────────────────────┐     ┌────────────────────────────────┐
│   External APIs         │     │  arr Services (LAN)            │
│                         │     │                                │
│  TMDB (movie/TV search) │     │  Radarr :7878 /api/v3/movie    │
│  MusicBrainz (music)    │     │  Sonarr :8989 /api/v3/series   │
│                         │     │  Lidarr :8686 /api/v3/artist   │
└─────────────────────────┘     └────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `config_flow.py` | 4-step wizard: TMDB → Radarr → Sonarr → Lidarr; validates each connection before accepting | `ConfigFlow` subclass, each step validates then advances |
| `coordinator.py` | Polls arr services every 5 min for library counts; exposes async search and request methods | `DataUpdateCoordinator` subclass with extra async methods |
| `sensor.py` | Exposes coordinator data as HA sensor entities so hass.states is populated | `CoordinatorEntity` + `SensorEntity` per arr service |
| `__init__.py` | Wires coordinator → sensors; registers WebSocket commands; serves frontend JS | `async_setup_entry`, `websocket_api.async_register_command` |
| `requestarr-card.js` | Tabbed search/request UI; reads sensor state; calls WebSocket commands | LitElement, `hass.connection.sendMessagePromise` |

## Recommended Project Structure

```
custom_components/requestarr/
├── __init__.py            # Entry setup, WS command registration, static path
├── config_flow.py         # 4-step ConfigFlow with live validation
├── const.py               # All constants: URLs, keys, defaults, WS command names
├── coordinator.py         # DataUpdateCoordinator + search/request API methods
├── sensor.py              # CoordinatorEntity sensors for library counts
├── services.yaml          # Service schema definitions (for UI display)
├── strings.json           # UI strings for config flow steps
├── translations/
│   └── en.json            # English translations
└── frontend/
    └── requestarr-card.js # Single-file LitElement card (no build step)
```

### Structure Rationale

- **coordinator.py holds all API logic:** Search, request, and poll all use the same aiohttp session management and API key config. Keeping it in one file prevents duplication and ensures a single source of truth for API credentials.
- **WebSocket commands registered in `__init__.py`:** Commands are integration-scoped (not entity-scoped), so they belong at setup time where the coordinator reference is available via closure or `hass.data`.
- **Single frontend JS file:** HACS convention enforced by project constraints — no npm, no webpack. LitElement is borrowed from HA's internal instance via `customElements.get("hui-masonry-view")`.
- **services.yaml separate from code:** HA reads this for UI descriptions and field type hints in the developer tools panel, but the actual schema is validated in Python via voluptuous.

## Architectural Patterns

### Pattern 1: WebSocket Commands for Search (not `hass.callService`)

**What:** Register custom WebSocket commands via `websocket_api.async_register_command`. The frontend card calls these with `hass.connection.sendMessagePromise` and awaits a result dict. This is the correct pattern for actions that return data back to the UI.

**When to use:** Any time the card needs to get data back from the backend synchronously — search results, request status, quality profiles. `hass.callService` is fire-and-forget and cannot return data to the caller.

**Trade-offs:** Slightly more boilerplate (backend decorator + frontend Promise); pays off immediately because search must return results to display in the card.

**Example (backend — `__init__.py`):**
```python
from homeassistant.components import websocket_api
import voluptuous as vol

@websocket_api.websocket_command(
    {
        vol.Required("type"): "requestarr/search",
        vol.Required("query"): str,
        vol.Required("media_type"): vol.In(["movie", "tv", "music"]),
    }
)
@websocket_api.async_response
async def ws_search(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Handle search WebSocket command."""
    coordinator: RequestarrCoordinator = hass.data[DOMAIN][
        next(iter(hass.data[DOMAIN]))
    ]
    results = await coordinator.async_search(msg["query"], msg["media_type"])
    connection.send_result(msg["id"], {"results": results})
```

**Example (frontend — `requestarr-card.js`):**
```javascript
async _doSearch() {
  this._searching = true;
  try {
    const response = await this.hass.connection.sendMessagePromise({
      type: "requestarr/search",
      query: this._searchQuery,
      media_type: this._activeTab === "movies" ? "movie"
                  : this._activeTab === "tv" ? "tv" : "music",
    });
    this._searchResults = response.results;
  } finally {
    this._searching = false;
  }
}
```

### Pattern 2: `hass.callService` for Request Submission (fire-and-forget)

**What:** Register HA services (`requestarr.request_movie`, `requestarr.request_series`, `requestarr.request_music`) for submit-request actions. The card calls these via `hass.callService`. No return value needed — the coordinator handles submission and the sensor states reflect the outcome on next poll.

**When to use:** Actions where the card doesn't need an immediate programmatic response — submission is sufficient. Works with HA automations as a bonus: users can automate media requests.

**Trade-offs:** Simpler than WebSocket for this case; fire-and-forget means error feedback must come from UI notification events or sensor state changes.

**Example (backend — `__init__.py`):**
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = RequestarrCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    async def handle_request_movie(call: ServiceCall) -> None:
        tmdb_id = call.data["tmdb_id"]
        await coordinator.async_request_movie(tmdb_id)

    hass.services.async_register(
        DOMAIN, "request_movie", handle_request_movie,
        schema=vol.Schema({vol.Required("tmdb_id"): int}),
    )
    # register request_series, request_music similarly
    websocket_api.async_register_command(hass, ws_search)
    websocket_api.async_register_command(hass, ws_request_media)
    ...
```

**Example (frontend — `requestarr-card.js`):**
```javascript
_requestItem(item) {
  const service = this._activeTab === "movies" ? "request_movie" : "request_series";
  this.hass.callService("requestarr", service, { tmdb_id: item.id });
  // Optimistic UI: show "Requested" state immediately
  this._requestedIds = { ...this._requestedIds, [item.id]: true };
}
```

### Pattern 3: Config Flow with Live Validation

**What:** Each config flow step uses `async_step_X` to accept user input, validate it against the live service (test HTTP connection, not just format), and only advance on success. Errors surface in the form via the `errors` dict.

**When to use:** Always for external service credentials — catching bad URLs/keys at config time prevents cryptic sensor-unavailable states later.

**Trade-offs:** Requires real API calls during config (aiohttp in flow steps). Must handle timeout/connection errors gracefully and map them to user-readable error codes in `strings.json`.

**Example (coordinator call in config flow):**
```python
async def async_step_radarr(self, user_input=None):
    errors = {}
    if user_input is not None:
        url = user_input.get(CONF_RADARR_URL, "")
        key = user_input.get(CONF_RADARR_API_KEY, "")
        if url and key:
            ok = await _test_arr_connection(url, key, "movie")
            if not ok:
                errors["base"] = "cannot_connect"
        if not errors:
            self._data.update(user_input)
            return await self.async_step_sonarr()
    return self.async_show_form(
        step_id="radarr", data_schema=STEP_RADARR_SCHEMA, errors=errors
    )
```

### Pattern 4: Arr Service Add Workflow (Quality Profile Bootstrap)

**What:** Adding a movie/series to Radarr/Sonarr requires a `qualityProfileId` and `rootFolderPath` that must be fetched from the service first. Fetch these at coordinator init time (or config flow time) and cache them. Use the first available profile/folder as the default.

**When to use:** Every `POST /api/v3/movie` or `POST /api/v3/series` call. Failing to fetch these first is the #1 cause of API errors.

**Trade-offs:** Adds one extra GET per arr service at startup; trivial cost for correctness.

**Example:**
```python
async def _async_fetch_radarr_defaults(self, session) -> dict:
    """Fetch quality profiles and root folders from Radarr."""
    headers = {"X-Api-Key": self._radarr_api_key}
    profiles = await self._get_json(session, f"{self._radarr_url}/api/v3/qualityProfile", headers)
    folders = await self._get_json(session, f"{self._radarr_url}/api/v3/rootFolder", headers)
    return {
        "quality_profile_id": profiles[0]["id"] if profiles else 1,
        "root_folder_path": folders[0]["path"] if folders else "/movies",
    }
```

## Data Flow

### Search Flow (Card → Backend → TMDB/MusicBrainz → Card)

```
[User types query + clicks Search]
        ↓
[requestarr-card._doSearch()]
        ↓ hass.connection.sendMessagePromise({type: "requestarr/search", ...})
[WebSocket: HA Core routes to ws_search handler]
        ↓
[RequestarrCoordinator.async_search(query, media_type)]
        ↓ aiohttp GET
[TMDB /search/movie  OR  MusicBrainz /ws/2/artist]
        ↓ JSON response
[Coordinator normalizes results → list of dicts]
        ↓ connection.send_result(msg["id"], {"results": [...]})
[WebSocket response resolves Promise in card]
        ↓
[Card sets this._searchResults → LitElement re-renders]
[User sees poster grid]
```

### Request Flow (Card → Backend → Radarr/Sonarr/Lidarr)

```
[User clicks Request on a result item]
        ↓
[requestarr-card._requestItem(item)]
        ↓ hass.callService("requestarr", "request_movie", {tmdb_id: X})
[HA routes to handle_request_movie service handler]
        ↓
[RequestarrCoordinator.async_request_movie(tmdb_id)]
        ↓ GET /api/v3/movie?tmdbId=X  (check already exists)
        ↓ GET /api/v3/qualityProfile   (get default profile)
        ↓ POST /api/v3/movie            (submit request)
[Radarr accepts; coordinator returns True]
        ↓
[Card shows optimistic "Requested" badge immediately]
[Next coordinator poll (≤5 min) refreshes library count sensor]
```

### Coordinator Poll Flow (Background → Sensors → Card Stats)

```
[Timer fires every 300s]
        ↓
[RequestarrCoordinator._async_update_data()]
        ↓ GET /api/v3/movie  (Radarr)
        ↓ GET /api/v3/series (Sonarr)
        ↓ GET /api/v3/artist (Lidarr)
[Returns dict: {radarr_movies: N, sonarr_series: N, lidarr_artists: N}]
        ↓
[CoordinatorEntity sensors read coordinator.data]
[sensor.requestarr_radarr_movies state = N]
        ↓ HA state machine notifies frontend
[Card reads hass.states["sensor.requestarr_radarr_movies"].state]
[Stats bar re-renders with new counts]
```

## Suggested Build Order

Dependencies drive this order. Each phase unblocks the next.

| Phase | Build | Why This Order |
|-------|-------|----------------|
| 1 | Config flow validation (TMDB + arr connection tests) | Must work before coordinator can fetch anything meaningful |
| 2 | Coordinator: library count polling + arr defaults cache | Sensors depend on coordinator; WS commands depend on coordinator's API methods |
| 3 | Sensor entities (library counts in hass.states) | Card's stats bar depends on sensor state; validates coordinator is wired correctly |
| 4 | WebSocket command: search | Requires coordinator `async_search()` method; unblocks card search feature |
| 5 | WebSocket command / service: request media | Requires arr defaults cache from Phase 2; coordinator `async_request_*` methods |
| 6 | Card: search UI wired to WS command | Requires Phase 4 backend; card already has placeholder `_doSearch` |
| 7 | Card: request UI wired to service call | Requires Phase 5 backend; card already has placeholder `_requestItem` |
| 8 | Card: "already in library" / "already requested" detection | Requires Phases 4+5 to first know what's in the library |

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| TMDB | REST GET, api_key query param | Free; `https://api.themoviedb.org/3/search/{movie,tv,multi}`; returns poster_path, title, release_date, tmdb_id |
| MusicBrainz | REST GET, no auth, User-Agent required | `https://musicbrainz.org/ws/2/artist?query=X&fmt=json`; rate limit 1 req/sec; must send User-Agent header |
| Radarr v3 | REST with X-Api-Key header | POST `/api/v3/movie` requires qualityProfileId + rootFolderPath; fetch these first |
| Sonarr v3 | REST with X-Api-Key header | POST `/api/v3/series` requires tvdbId (not tmdbId) — TMDB results must be mapped to TVDB ID via TMDB's `/tv/{id}/external_ids` endpoint |
| Lidarr v3 | REST with X-Api-Key header | POST `/api/v3/artist` requires MusicBrainz artist ID (`foreignArtistId`) |

### Critical Integration Gotcha: Sonarr Needs TVDB IDs

TMDB search returns TMDB IDs. Sonarr v3 requires TVDB IDs, not TMDB IDs. To add a TV series to Sonarr via TMDB search:

1. Search TMDB `/search/tv` → get `tmdb_id`
2. Fetch TMDB `/tv/{tmdb_id}/external_ids` → get `tvdb_id`
3. Use `tvdb_id` in Sonarr POST

This extra step must be implemented in `coordinator.async_request_series()`.

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Card ↔ HA backend (search) | WebSocket sendMessagePromise | Async, returns data; use for all query operations |
| Card ↔ HA backend (request) | hass.callService | Fire-and-forget; error feedback via UI notification events |
| Card ↔ sensor entities | hass.states object | Read-only; card polls hass.states for library count display |
| Coordinator ↔ arr APIs | aiohttp ClientSession | Reuse session within a single `_async_update_data` call; create fresh session per WS command |
| Config flow ↔ arr APIs | aiohttp (one-shot) | Test connections at config time; close session after each test |

## Anti-Patterns

### Anti-Pattern 1: Using `hass.callService` for Search

**What people do:** Call a HA service for TMDB search and try to read results from a sensor entity that gets populated by the service handler.

**Why it's wrong:** Service calls are fire-and-forget. There is no mechanism to return data to the caller. Workarounds (polling a temporary sensor, storing results in `hass.data` and reading via another WS call) are fragile and convoluted.

**Do this instead:** Use `websocket_api.async_register_command` + `hass.connection.sendMessagePromise`. This is the HA-native pattern for frontend-initiated queries that need results back.

### Anti-Pattern 2: Creating a New aiohttp Session Per Poll Cycle

**What people do:** Create `async with aiohttp.ClientSession() as session:` inside `_async_update_data`, and also inside each WebSocket handler, with no reuse.

**Why it's wrong:** Session creation has overhead. More importantly, the coordinator's aiohttp usage is already in the scaffold — it is fine within a single method scope, but creating sessions in every WS command handler compounds overhead under concurrent requests.

**Do this instead:** Create one `aiohttp.ClientSession` per `_async_update_data` call (already done in scaffold). For WS command handlers, create a single session for the duration of that handler only. Do NOT store a long-lived session as an instance variable — sessions are not thread-safe across coroutines and must be created in the async context.

### Anti-Pattern 3: Hardcoding qualityProfileId = 1 and rootFolderPath = "/movies"

**What people do:** Skip the preflight GET calls to `/api/v3/qualityProfile` and `/api/v3/rootFolder` and assume defaults.

**Why it's wrong:** User's Radarr may have no profile with ID 1, or their root folder path may be `/data/media` or `/downloads`. This fails silently — Radarr returns a 200 but doesn't actually add the movie, or returns a 400 with a cryptic error.

**Do this instead:** Fetch quality profiles and root folders at coordinator init. Cache the first available values as defaults. Optionally expose them as options in the config flow so users can choose.

### Anti-Pattern 4: Registering WebSocket Commands in a Platform's `async_setup_entry`

**What people do:** Try to register WS commands in `sensor.py`'s `async_setup_entry` or in an entity class.

**Why it's wrong:** Platform setup can run multiple times (if multiple config entries exist). The command would be registered multiple times, causing errors or undefined behavior. WS commands are integration-global, not per-entry.

**Do this instead:** Register in `__init__.py`'s `async_setup_entry`. Guard against double-registration by checking if command is already registered, or use `async_setup` (called once) if the integration supports it.

### Anti-Pattern 5: Direct TMDB Calls from the Card (Bypassing Backend)

**What people do:** Put the TMDB API key in the card's JavaScript (via `hass.states` exposure or hardcoded) and call TMDB directly from the browser.

**Why it's wrong:** Exposes the TMDB API key in the browser. Bypasses HA's auth model. Makes the key visible in HA's state machine. Breaks the architecture — the backend exists precisely to hold credentials.

**Do this instead:** All external API calls go through the coordinator via WebSocket commands. The card never has access to raw API keys.

## Scaling Considerations

This integration runs in a single-household Home Assistant instance. Scaling in the traditional sense (thousands of concurrent users) does not apply. The relevant scaling axis is **number of configured arr services** and **concurrent card users**.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 arr service | Current scaffold is sufficient |
| 3 arr services (Radarr + Sonarr + Lidarr) | Coordinator polls all in parallel within one update cycle; aiohttp handles this fine |
| Multiple household members using card simultaneously | Each WS command spawns an independent coroutine; aiohttp handles concurrent requests; no shared mutable state beyond `coordinator.data` which is read-only from WS handlers |
| Many search requests in quick succession | MusicBrainz rate limit (1 req/sec) is the binding constraint; add debounce on search input (300ms minimum) |

### Scaling Priorities

1. **First bottleneck:** MusicBrainz rate limiting under rapid music searches. Mitigation: debounce input in card (wait 300ms after last keystroke before calling WS).
2. **Second bottleneck:** Coordinator poll interval. Default 300s is fine for library counts. If users want near-real-time "already in library" detection, consider reducing to 60s or triggering a manual refresh after a request is submitted.

## Sources

- Home Assistant Developer Docs — Extending the WebSocket API: https://developers.home-assistant.io/docs/frontend/extending/websocket-api/
- Home Assistant Developer Docs — Integration Service Actions: https://developers.home-assistant.io/docs/dev_101_services/
- Home Assistant Custom Card Developer Docs: https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/
- Radarr API Docs: https://radarr.video/docs/api/
- Sonarr API Docs: https://sonarr.tv/docs/api/
- MusicBrainz API Rate Limiting: https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
- HA Developer Community — Embedded Lovelace Card Guide: https://community.home-assistant.io/t/developer-guide-embedded-lovelace-card-in-a-home-assistant-integration/974909
- Existing scaffold: `/home/dab/Projects/ha-requestarr/custom_components/requestarr/`

---
*Architecture research for: Requestarr — Home Assistant HACS media request integration*
*Researched: 2026-02-19*
