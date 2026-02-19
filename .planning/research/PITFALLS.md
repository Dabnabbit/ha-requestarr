# Pitfalls Research

**Domain:** Home Assistant HACS integration + Lovelace card wrapping external APIs (TMDB, Radarr, Sonarr, Lidarr, MusicBrainz)
**Researched:** 2026-02-19
**Confidence:** HIGH (most findings verified with official HA developer docs or GitHub issues; MEDIUM/LOW flagged inline)

---

## Critical Pitfalls

### Pitfall 1: Sonarr Requires TVDB ID, Not TMDB ID

**What goes wrong:**
The card searches TMDB and returns a `tv` result with a `tmdbId`. When the backend tries to add that series to Sonarr using the TMDB ID, Sonarr's API v3 `/series` endpoint rejects it with a 400 validation error: `'Tvdb Id' must be greater than '0'`. Sonarr is exclusively TVDB-native. TMDB IDs are not accepted as the primary add-series identifier.

**Why it happens:**
TMDB is the search source for movies AND TV (since it covers both well with poster art). Developers assume the TMDB ID can pass straight through to all three arr services. Radarr accepts TMDB ID directly — Sonarr does not. This asymmetry is invisible until the first real request attempt.

**How to avoid:**
Add a two-step flow for Sonarr requests:
1. Use Sonarr's `/api/v3/series/lookup?term=<title>` or `/api/v3/series/lookup?term=tvdb:<tvdbId>` endpoint to resolve the TVDB ID.
2. The lookup returns a series object that contains `tvdbId`. Use that in the POST to `/api/v3/series`.

The TMDB search result's title can be used as the `term` parameter in Sonarr's lookup. The lookup response includes the full series object needed for the subsequent add call (including `tvdbId`, `images`, `seasons`, etc.) — pass it back almost verbatim with `rootFolderPath`, `qualityProfileId`, and `monitored` added.

**Warning signs:**
- Any code path that calls `POST /api/v3/series` with only a `tmdbId` field will fail silently or with a 400 error.
- If `async_request_series` in the coordinator passes `tmdb_id` directly into the Sonarr body, this is the bug.

**Phase to address:**
Sonarr request implementation phase. Before writing any Sonarr POST logic, implement the lookup-then-add two-step pattern.

---

### Pitfall 2: `hass.http.register_static_path` Is Removed in HA 2025.7

**What goes wrong:**
The scaffolded `__init__.py` calls `hass.http.register_static_path(...)` synchronously. This function was deprecated in June 2024 and removed in Home Assistant 2025.7. Any HA instance on 2025.7+ will fail to set up the integration entirely — the card JS will never register, and users will see "Integration failed to set up."

**Why it happens:**
The HACS template this project was scaffolded from used the legacy sync API. The deprecation warning appears in HA logs but doesn't fail setup until removal in 2025.7. Developers who test on older HA versions won't notice.

**How to avoid:**
Replace the call immediately with the async version:

```python
from homeassistant.components.http import StaticPathConfig

async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register the frontend card resources."""
    frontend_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            FRONTEND_SCRIPT_URL,
            str(frontend_path / f"{DOMAIN}-card.js"),
            cache_headers=True,
        )
    ])
```

**Warning signs:**
- Current `__init__.py` calls `hass.http.register_static_path` (no `async_`, no `await`).
- HA logs show: `"Detected that custom integration 'requestarr' calls hass.http.register_static_path which is deprecated because it does blocking I/O in the event loop."` — this means the deprecation period is active and removal is imminent.

**Phase to address:**
Fix this in the very first implementation phase, before any other work. It is a pre-existing scaffold bug that will break all HA 2025.7+ installations.

---

### Pitfall 3: Coordinator Creates a New `aiohttp.ClientSession` Per Update Cycle

**What goes wrong:**
The scaffolded coordinator opens `async with aiohttp.ClientSession() as session:` inside `_async_update_data()`, which runs every 5 minutes (and also on each search call). This creates and destroys a new session on every poll. Each session carries its own connection pool. Over time this leaks file descriptors, slows the event loop, and can eventually cause "too many open connections" errors or coordinator failures after several hours.

**Why it happens:**
The `async with` context manager pattern looks correct in isolation. Developers familiar with simple scripts don't realize that aiohttp's session pooling only provides a benefit when the session is reused. HA explicitly documents that integrations should use `async_get_clientsession(hass)` for the shared session.

**How to avoid:**
Remove the `aiohttp.ClientSession()` instantiation from all methods. Use HA's shared session:

```python
from homeassistant.helpers.aiohttp_client import async_get_clientsession

class RequestarrCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(...)
        self._session = async_get_clientsession(hass)
```

Then in every method, use `self._session.get(...)` directly without the `async with aiohttp.ClientSession()` wrapper.

**Warning signs:**
- Any method that opens `async with aiohttp.ClientSession()` as a local variable.
- Coordinator becomes unavailable after several hours without a HA restart (documented HA community issue).

**Phase to address:**
Fix alongside the `register_static_path` migration — both are scaffold bugs, fix both in the same phase.

---

### Pitfall 4: Arr "Add" APIs Require More Than Just the Media ID

**What goes wrong:**
The coordinator's `async_request_movie` and `async_request_series` stubs currently only have the TMDB ID. A real POST to `/api/v3/movie` (Radarr) or `/api/v3/series` (Sonarr) with only `tmdbId` will fail with 400 or a `System.NullReferenceException` from the arr service. These endpoints require:

For **Radarr** (`POST /api/v3/movie`):
- `tmdbId` (int)
- `title` (string)
- `titleSlug` (string)
- `images` (array — from the lookup response)
- `qualityProfileId` (int — must be fetched from `/api/v3/qualityprofile`)
- `rootFolderPath` (string — must be fetched from `/api/v3/rootfolder`)
- `monitored` (bool)
- `addOptions.searchForMovie` (bool)

For **Sonarr** (`POST /api/v3/series`):
- `tvdbId` (int — not TMDB ID, see Pitfall 1)
- All fields from the lookup response (title, images, seasons, etc.)
- `qualityProfileId`, `languageProfileId`, `rootFolderPath`, `monitored`, `seasonFolder`, `addOptions`

For **Lidarr** (`POST /api/v1/artist`):
- `foreignArtistId` (MusicBrainz Artist ID — string)
- `metadataProfileId` (int)
- `qualityProfileId` (int)
- `rootFolderPath` (string)
- `monitored` (bool)
- Artist metadata object from Lidarr's own lookup

**Why it happens:**
The `qualityProfileId` and `rootFolderPath` are not known at config time without fetching them from each service. Developers assume some default (like ID=1) will work. But users may have deleted the default profiles, or their root folder may differ from any assumed path.

**How to avoid:**
During config flow validation, fetch and store the first available `rootFolderPath` and `qualityProfileId` from each configured service. Store them in config entry data. Expose them as optional settings in an options flow so users can change them. Use the arr lookup endpoints to build the full add payload rather than constructing it manually.

**Warning signs:**
- `async_request_movie` only takes `tmdb_id: int` as its signature — no title, no images, no profiles.
- Any hardcoded `qualityProfileId: 1` in request bodies.
- Lookup calls missing before the POST.

**Phase to address:**
Request submission implementation phase. Do NOT build the add-to-arr feature without first building the lookup-and-profile-fetch chain.

---

### Pitfall 5: MusicBrainz Blocks Requests Without a Proper User-Agent Header

**What goes wrong:**
MusicBrainz enforces a strict rate limit of 1 request per second per IP, and applications that exceed it get all requests declined (HTTP 503) until the rate drops — not a graceful 25%-rejection. Additionally, requests without an application-identifying `User-Agent` header (e.g., a generic aiohttp default) may be throttled or blocked application-wide.

**Why it happens:**
The MusicBrainz docs are clear, but developers default to whatever aiohttp sends (which is something like `Python/3.11 aiohttp/3.9`). If MusicBrainz identifies a misbehaving user-agent, it applies extra throttling to that user-agent string globally.

**How to avoid:**
Set a descriptive User-Agent for all MusicBrainz requests:

```python
MUSICBRAINZ_USER_AGENT = "Requestarr/0.1.0 ( https://github.com/Dabentz/ha-requestarr )"

headers = {"User-Agent": MUSICBRAINZ_USER_AGENT}
```

Since music search is user-initiated (not polling), rate limiting should not be a practical issue for household use. But the User-Agent header is mandatory for good standing.

**Warning signs:**
- MusicBrainz requests using the shared HA session without a custom `User-Agent` header.
- Any polling of MusicBrainz (only search on user action — never poll MusicBrainz).

**Phase to address:**
Music/Lidarr implementation phase.

---

## Moderate Pitfalls

### Pitfall 6: TMDB API Key Exposed in Browser Network Traffic

**What goes wrong:**
If the Lovelace card calls TMDB directly from JavaScript (e.g., `fetch('https://api.themoviedb.org/3/search/movie?api_key=...')`), the API key is visible in browser developer tools network tab. Anyone on the household network can see it.

**How to avoid:**
Route all TMDB search through a Home Assistant service call to the backend coordinator. The coordinator already has the API key in memory from the config entry. The card calls `hass.callService('requestarr', 'search', {query, media_type})` and the backend returns results via a HA state or WebSocket response. The API key never touches the browser.

The current scaffold's `_doSearch()` has a TODO for this — fill it with a proper service call, not a direct fetch.

**Warning signs:**
- Any `fetch('https://api.themoviedb.org...')` or `XMLHttpRequest` to TMDB in the JS card.
- The TMDB API key appearing in browser network logs.

**Phase to address:**
Search implementation phase. Establish the service-call pattern for search before implementing any TMDB calls.

---

### Pitfall 7: `iot_class` Mismatch — Integration Uses Cloud API but Declares `local_polling`

**What goes wrong:**
The manifest currently declares `"iot_class": "local_polling"`. The integration polls arr services locally (correct for `local_polling`), but it also uses TMDB which is a cloud API. hassfest may warn about this; more importantly it misleads users who try to use the integration offline.

**How to avoid:**
Since TMDB is required (it's the search backbone) and it's a cloud API, the correct `iot_class` is `"cloud_polling"`. The arr services being local doesn't override the fact that a cloud dependency exists. This also accurately signals to users that internet access is required.

**Warning signs:**
- `"iot_class": "local_polling"` in manifest.json while TMDB is a mandatory dependency.

**Phase to address:**
Fix in the manifest during the initial validation/CI pass.

---

### Pitfall 8: Config Flow Missing `unique_id` — Allows Multiple Identical Setups

**What goes wrong:**
Without calling `await self.async_set_unique_id(...)` and `self._abort_if_unique_id_configured()` in the config flow, users can add the integration multiple times. This creates duplicate sensors, duplicate service registrations, and confusing entity naming. The strings.json already defines an `already_configured` abort key — but the code never uses it.

**How to avoid:**
In `async_step_user`, after validating the TMDB API key, set a unique ID derived from something stable. Since there's no device ID, use the TMDB API key itself (it's user-specific and stable):

```python
await self.async_set_unique_id(user_input[CONF_TMDB_API_KEY])
self._abort_if_unique_id_configured()
```

**Warning signs:**
- No `async_set_unique_id` call anywhere in `config_flow.py`.
- The `already_configured` abort in `strings.json` is defined but unreachable.

**Phase to address:**
Config flow implementation phase.

---

### Pitfall 9: Multi-Step Config Flow Chaining Bug — Steps Called Directly Instead of Returned

**What goes wrong:**
In the scaffold, `async_step_user` calls `return await self.async_step_radarr()` when `user_input is not None`. This means Radarr's step shows immediately when the user submits the TMDB step — which is correct. However, if `async_step_radarr` is called this way and the user has NO input yet (first visit), `user_input` is `None` and the form is shown. This works but it means the step method is called twice in sequence synchronously. If any step has side effects (like API calls during form rendering), they'll fire immediately on form display before the user interacts.

The deeper risk: connection validation (TODO items in the scaffold) must only run when `user_input is not None`. If validation is ever added to the initial `if user_input is not None` block but the direct-call chain skips it, validation silently gets bypassed.

**How to avoid:**
Keep the chaining pattern but ensure ALL validation is strictly inside `if user_input is not None`. Never put API calls or side effects in the form-display branch. Keep each step's form display pure and stateless.

**Warning signs:**
- API validation calls outside the `if user_input is not None` guard.
- Connection tests firing when the form is first displayed (before user input).

**Phase to address:**
Config flow validation implementation phase (when TODO validation is implemented).

---

### Pitfall 10: Options Flow / Reconfigure Not Implemented — Users Cannot Change API Keys

**What goes wrong:**
After setup, users have no way to update URLs or API keys if they change. The only recovery is deleting and re-adding the integration. This is poor UX and a common complaint for HACS integrations. HA 2025+ deprecated the pattern of setting `config_entry` explicitly in OptionsFlowHandler — integrations that do this will get warnings in HA 2025.1+ and need migration.

**How to avoid:**
Implement a `reconfigure` step (preferred for changing setup data like URLs/API keys) or an `OptionsFlow` (for truly optional settings). The reconfigure step is the modern approach:

```python
async def async_step_reconfigure(self, user_input=None):
    # Allows changing TMDB key, arr URLs/keys
```

**Warning signs:**
- No `OptionsFlowHandler` class in `config_flow.py`.
- No `async_step_reconfigure` method.
- No `"reconfigure_successful"` key in `strings.json`.

**Phase to address:**
Post-MVP polish phase. Not needed for initial ship but should be added before HACS submission.

---

### Pitfall 11: Card-to-Backend Communication Pattern Not Established

**What goes wrong:**
The card's `_doSearch()` and `_requestItem()` are both stubbed out. There are two valid patterns for card-backend communication:
1. `hass.callService(domain, service, data)` — fires a HA service, no response data returned to the card.
2. `hass.callWS({type: 'requestarr/search', ...})` — custom WebSocket command registered on the backend, returns data directly.

Using `hass.callService` for search is wrong because the card needs the search results back. Services in HA are fire-and-forget — they don't return data to the caller in any convenient way. Using WebSocket (`hass.callWS`) returns data synchronously to the JavaScript caller.

**Why it happens:**
Developers familiar with HA services assume `callService` covers all cases. It doesn't when you need return data (like search results).

**How to avoid:**
Register a custom WebSocket command for search in the backend using `websocket_api.async_register_command`:

```python
# In __init__.py or a websocket.py module:
from homeassistant.components import websocket_api

@websocket_api.websocket_command({
    vol.Required("type"): "requestarr/search",
    vol.Required("query"): str,
    vol.Required("media_type"): str,
})
@websocket_api.async_response
async def ws_search(hass, connection, msg):
    coordinator = hass.data[DOMAIN][...]
    results = await coordinator.async_search_tmdb(msg["query"], msg["media_type"])
    connection.send_result(msg["id"], results)
```

In the card JS:
```javascript
const results = await this.hass.callWS({
    type: "requestarr/search",
    query: this._searchQuery,
    media_type: mediaType,
});
this._searchResults = results;
```

Use `callService` only for fire-and-forget actions like "submit request to Radarr" where the card only needs success/failure.

**Warning signs:**
- `_doSearch()` trying to use `hass.callService` for search.
- `_doSearch()` making direct `fetch()` calls to TMDB (exposes API key, see Pitfall 6).

**Phase to address:**
Search implementation phase — establish the WebSocket pattern before implementing search.

---

### Pitfall 12: Translations Missing for Config Flow Steps — hassfest Failure

**What goes wrong:**
hassfest validates that every step defined in `strings.json` has a corresponding step method, and that every data key in a step has a translation. If `strings.json` and `en.json` diverge from the actual config flow steps (currently they're in sync, but future additions may drift), hassfest fails CI. Also, `en.json` must be a copy of `strings.json` (the source of truth) — they currently appear to be identical, which is correct, but this must be maintained.

**How to avoid:**
- When adding a new step (e.g., reconfigure, options), add it to both `strings.json` AND `translations/en.json` simultaneously.
- When adding a new config key to a step schema, add its label to both translation files.
- Run `hacs/action` and `hassfest` CI on every PR that touches config_flow.py or translation files.

**Warning signs:**
- `strings.json` has a step that `config_flow.py` doesn't implement (or vice versa).
- `en.json` is not byte-for-byte identical to `strings.json`.
- CI fails on translation validation with "extra keys not allowed".

**Phase to address:**
Every implementation phase. Treat translation sync as part of the definition-of-done for any config flow change.

---

## Minor Pitfalls

### Pitfall 13: Sensor `device_info` Missing — Sensors Float Without a Device

**What goes wrong:**
The sensor entities don't define `device_info`, so they appear as standalone entities with no parent device in the HA device registry. This is acceptable but means the integration won't group its sensors under a single "Requestarr" device entry in the UI. It's not a hassfest failure but is a quality expectation for published integrations.

**How to avoid:**
Add `device_info` to the sensor entity:

```python
@property
def device_info(self):
    return DeviceInfo(
        identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
        name="Requestarr",
        manufacturer="Community",
        model="Media Request Manager",
        entry_type=DeviceEntryType.SERVICE,
    )
```

**Phase to address:**
Sensor polish phase.

---

### Pitfall 14: `FRONTEND_SCRIPT_URL` Uses `/hacsfiles/` Path — Only Works When HACS Is Installed

**What goes wrong:**
`const.py` defines `FRONTEND_SCRIPT_URL = f"/hacsfiles/{DOMAIN}/{DOMAIN}-card.js"`. This path is served by HACS's static file server, not by the integration's own `register_static_paths` call. The `__init__.py` registers the file at that URL via `hass.http.register_static_path`. These two are inconsistent: the path `/hacsfiles/...` is conventionally managed by HACS itself, not by the integration's `register_static_paths`. For users installing via HACS, HACS handles file serving. For users installing manually (dropping into `custom_components/`), the integration's `register_static_paths` call covers it. Both paths should work, but the URL must be consistent with how the resource is added to Lovelace.

**How to avoid:**
If the integration self-registers via `async_register_static_paths`, use a URL like `/requestarr/requestarr-card.js` (integration-owned path). If relying on HACS file serving, don't call `register_static_paths` at all and let HACS manage it. Pick one approach and be consistent. Mixing them causes the card to 404 in one installation mode.

**Warning signs:**
- `FRONTEND_SCRIPT_URL` starts with `/hacsfiles/` but is also used in `hass.http.register_static_path(s)`.
- Card not loading for manual installs.

**Phase to address:**
Frontend serving phase — resolve the URL strategy before implementing the card properly.

---

### Pitfall 15: Image HTTPS/HTTP Mixed Content When HA Is on HTTPS

**What goes wrong:**
The card renders `<img src="https://image.tmdb.org/t/p/w92${item.poster_path}">`. TMDB image CDN serves over HTTPS, so this is fine. However, if the TMDB image URL somehow returns HTTP (not expected, but possible with future CDN changes or certain poster paths), and the HA instance is served over HTTPS, browser mixed content blocking will silently refuse to load the image.

**How to avoid:**
Always use `https://image.tmdb.org` (no `http://`). Never construct image URLs with a protocol variable that could be HTTP. The current scaffold correctly hardcodes `https://image.tmdb.org` — maintain this.

**Phase to address:**
Verify during card implementation review.

---

### Pitfall 16: `async_config_entry_first_refresh` Blocks HA Startup If Arr Services Are Offline

**What goes wrong:**
`async_setup_entry` calls `await coordinator.async_config_entry_first_refresh()`. If all arr services are offline (network blip at startup), this raises `ConfigEntryNotReady`, which is the correct exception. HA will retry. However, if the implementation raises a generic `Exception` instead, the integration fails permanently until HA restarts. The coordinator's current broad `except Exception as err: raise UpdateFailed(...)` converts failures to `UpdateFailed`, which the first-refresh call correctly re-raises as `ConfigEntryNotReady`. This chain is correct as-is, but it's fragile — if any exception escapes `_async_update_data` without being caught, setup fails permanently.

**How to avoid:**
Ensure `_async_update_data` has a top-level `except Exception` that always raises `UpdateFailed`. Never raise other exception types from `_async_update_data`.

**Phase to address:**
Error handling review phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode `qualityProfileId=1` for arr requests | No extra API call at request time | Fails if user deleted default quality profiles | Never — fetch dynamically |
| Direct `fetch()` to TMDB from card JS | Simpler card code | API key exposed in browser | Never — use backend service |
| Skip `unique_id` in config flow | Simpler config flow | Duplicate integration entries possible | Never for published HACS integrations |
| Skip options/reconfigure flow | Faster initial ship | Users must delete+re-add to change any setting | Acceptable for internal/MVP only |
| New `aiohttp.ClientSession()` per request | Straightforward code | Resource leak, coordinator instability over time | Never — use `async_get_clientsession` |
| Skip `device_info` on sensors | Less code | Sensors float without device grouping | Acceptable for MVP, fix before HACS submission |
| Skip MusicBrainz User-Agent header | One less line | Risk of application-level throttle by MB | Never — trivial to add, costly to omit |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Sonarr | Posting `tmdbId` to `/api/v3/series` | Lookup series by title first, extract `tvdbId`, post that |
| Radarr | Only sending `tmdbId` without title, images, rootFolderPath, qualityProfileId | Fetch `/api/v3/movie/lookup?tmdbId=X` first, add profiles, then POST |
| Lidarr | Assuming `qualityProfileId=1` and `metadataProfileId=1` exist | Fetch `/api/v1/qualityprofile` and `/api/v1/metadataprofile` at config time |
| TMDB | Calling TMDB from card JavaScript | All TMDB calls go through backend coordinator via WebSocket command |
| MusicBrainz | Using default aiohttp User-Agent, polling instead of on-demand search | Set descriptive User-Agent, search only on user action (never poll) |
| HA HTTP | Using `hass.http.register_static_path` (sync, removed 2025.7) | Use `await hass.http.async_register_static_paths([StaticPathConfig(...)])` |
| HA aiohttp | `async with aiohttp.ClientSession()` in coordinator methods | Use `async_get_clientsession(hass)` once at init, reuse `self._session` |
| HA services | `hass.callService()` for search (no return value) | Register WebSocket command `hacs.callWS()` for operations that return data |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| New aiohttp session per coordinator update | Coordinator becomes unavailable after hours; HA logs show connection errors | Use `async_get_clientsession(hass)`, store as `self._session` | Hours to days of uptime |
| Polling MusicBrainz alongside arr services | MB returns HTTP 503; music search breaks for all users sharing the HA IP | Never poll MusicBrainz; search only on user action | First poll cycle (1 request/sec limit means polling at 5-min interval is fine BUT multiple users querying simultaneously multiplies requests) |
| Loading full arr library instead of just count | Slow coordinator updates, high memory if library is large | Only call `/api/v3/movie` to count movies at library scale; for large libraries use a count endpoint if available | Libraries > ~5,000 items |
| Unbounded search results from TMDB | Card renders hundreds of results; browser slows | Limit to `page=1` (default 20 results) from TMDB search; add a client-side cap | Searches for common terms like "the" |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| TMDB API key in JS card fetch calls | Key visible in browser dev tools to anyone on household network | Proxy all TMDB calls through HA backend service/WebSocket |
| Storing API keys in `hass.data` dict (not config entry) | Keys lost on HA restart if not persisted to config entry | Always read API keys from `self.config_entry.data`, which HA persists to disk |
| No URL validation in config flow | Users can configure arbitrary URLs; backend makes requests to them on user's network | Validate URL format with `voluptuous`; ensure scheme is `http` or `https` |
| Logging API keys | Keys appear in HA logs, log files | Never log `api_key` values; only log domain/host |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No "already in library" state on search results | Users request content that's already downloaded; confusing | Before rendering results, check arr library endpoints and mark items already present |
| No request feedback after clicking "Request" | User clicks button, nothing visible happens, clicks again creating duplicates | Show spinner on button, disable after click, show toast success/error |
| Tab switch clears search results | User searches movies, switches to TV tab, switches back — results gone | Clear results intentionally on tab switch (current behavior is correct — just note it's intentional) |
| Search fires on every keypress | API call rate goes through roof while user types | Debounce: wait 300ms after last keypress before calling search |
| Music tab searches TMDB for music | TMDB has minimal music data; results are poor | Route music tab to MusicBrainz search, not TMDB search |

---

## "Looks Done But Isn't" Checklist

- [ ] **Config flow validation:** Each step shows a form, collects data, and creates the entry — but connection to TMDB/arr services is never actually tested. Verify each step calls the respective service and displays errors on failure.
- [ ] **Search returns results:** The card renders the result list HTML — but `_doSearch()` sets `this._searchResults = []` and never populates it. Verify search actually calls backend and populates results.
- [ ] **Request button works:** `_requestItem()` dispatches a notification event — but never actually sends to Radarr/Sonarr/Lidarr. Verify the service call chain is complete end-to-end.
- [ ] **Sensors update:** Sensors exist and show `None` — but coordinator returns `None` for all counts if the arr services aren't reachable. Verify sensors show real counts after connectivity is established.
- [ ] **Frontend card loads:** Card JS is registered at a URL — but unless the resource is also added to Lovelace resources (either via HACS or manual `configuration.yaml` entry), the card element is undefined. Verify card appears in the card picker.
- [ ] **HACS action passes:** CI runs `hacs/action` — but the integration is not yet registered in `home-assistant/brands`. Without brands registration, HACS will not list the integration in the default store (only installable via custom repo URL).
- [ ] **hassfest passes:** `hassfest` validates manifest keys, iot_class, translation files, and config flow consistency. Verify CI is green after any manifest or translation change.
- [ ] **Options/reconfigure exists:** Integration appears fully configured — but users have no way to update credentials without deleting and re-adding.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| `register_static_path` used on HA 2025.7+ | LOW | Replace with `async_register_static_paths` + `StaticPathConfig` in `__init__.py` |
| aiohttp session leak | LOW | Replace with `async_get_clientsession(hass)` pattern; no migration needed |
| Sonarr TVDB ID missing | MEDIUM | Add lookup step before Sonarr POST; requires finding where TMDB→Sonarr flow is wired and inserting the lookup |
| TMDB key exposed via direct card fetch | MEDIUM | Register WebSocket command on backend; update card JS to use `hass.callWS` |
| Missing unique_id in config flow | LOW | Add `async_set_unique_id` + `_abort_if_unique_id_configured` to `async_step_user` |
| Arr add payload missing required fields | HIGH | Requires redesigning the request flow: lookup → fetch profiles → build full payload → POST; existing stubs need full replacement |
| Not in HA brands repo | LOW | Submit PR to `home-assistant/brands` (quick if domain isn't taken) |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| `register_static_path` deprecated API | Phase 1: Scaffold fixes | HA logs show no deprecation warning on integration load |
| aiohttp session per request | Phase 1: Scaffold fixes | Coordinator stable after 24h; no session leak warnings |
| Config flow missing unique_id | Phase 2: Config flow implementation | Two installs of same integration shows "already configured" error |
| iot_class mismatch | Phase 2: Config flow implementation | hassfest passes without iot_class warning |
| Translation/strings sync | Phase 2 and every subsequent phase | hassfest CI passes green |
| TMDB key exposed in card | Phase 3: Search implementation | No TMDB requests visible in browser network tab |
| Card-to-backend communication pattern | Phase 3: Search implementation | `hass.callWS` roundtrip returns search results to card |
| Sonarr needs TVDB ID, not TMDB ID | Phase 4: Request submission | Sonarr series add succeeds without 400 error |
| Arr add payload missing required fields | Phase 4: Request submission | Radarr/Sonarr/Lidarr add calls succeed; fetch profiles at config time |
| MusicBrainz User-Agent | Phase 5: Music/Lidarr implementation | MusicBrainz responds 200 without throttle |
| Missing device_info on sensors | Phase 6: Polish | Sensors grouped under "Requestarr" device in HA device registry |
| No options/reconfigure flow | Phase 6: Polish | "Configure" button appears on integration card; credentials can be changed |
| HA brands repo registration | Pre-HACS submission | `hacs/action` passes; integration appears in HACS default store |

---

## Sources

- [HA Developer Docs: Inject websession (async_get_clientsession)](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/inject-websession/) — HIGH confidence
- [HA Developer Blog: async_register_static_paths migration (June 2024)](https://developers.home-assistant.io/blog/2024/06/18/async_register_static_paths/) — HIGH confidence
- [HACS issue #3828: register_static_path deprecated in HACS itself](https://github.com/hacs/integration/issues/3828) — HIGH confidence
- [Sonarr issue #7565: Can't add TV Series using TMDB ID](https://github.com/Sonarr/Sonarr/issues/7565) — HIGH confidence
- [Radarr issue #7095: NullReferenceException from missing required fields](https://github.com/Radarr/Radarr/issues/7095) — HIGH confidence
- [Radarr issue #5881: Required fields not annotated in API docs](https://github.com/Radarr/Radarr/issues/5881) — HIGH confidence
- [MusicBrainz API Rate Limiting docs](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting) — HIGH confidence
- [HA Developer Docs: Config flow handler](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/) — HIGH confidence
- [HA Developer Docs: Handling setup failures](https://developers.home-assistant.io/docs/integration_setup_failures/) — HIGH confidence
- [HA Developer Docs: Extending WebSocket API](https://developers.home-assistant.io/docs/frontend/extending/websocket-api/) — HIGH confidence
- [HA Developer Docs: Unique config entry](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/unique-config-entry/) — HIGH confidence
- [HACS integration requirements](https://www.hacs.xyz/docs/publish/integration/) — HIGH confidence
- [HACS issue #4314: options flow config_entry deprecated in HA 2025.1](https://github.com/hacs/integration/issues/4314) — HIGH confidence
- [TMDB API: CORS and rate limiting documentation](https://developer.themoviedb.org/docs/rate-limiting) — MEDIUM confidence (accessed via search result)
- [HA Frontend Docs: Custom card development](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/) — HIGH confidence
- [HA community: DataUpdateCoordinator unavailable after hours](https://community.home-assistant.io/t/dataupdatecoordinator-based-integrations-become-unavailable-after-a-few-hours/986502) — MEDIUM confidence

---
*Pitfalls research for: HACS integration wrapping TMDB + arr services (Radarr/Sonarr/Lidarr) with Lovelace card*
*Researched: 2026-02-19*
