# Phase 1: Config Flow + API Clients - Research

**Researched:** 2026-02-25
**Domain:** Home Assistant config flow, arr service API clients, DataUpdateCoordinator
**Confidence:** HIGH

## Summary

Phase 1 replaces the template scaffold's generic 2-step config flow and placeholder API client with a 3-step arr service wizard (Radarr, Sonarr, Lidarr) and a uniform API client using X-Api-Key authentication. Each step validates the connection live via `/system/status`, fetches quality profiles and root folders on success, and allows skipping with a checkbox. The coordinator polls library counts from all configured services every 5 minutes with partial failure tolerance.

The template already provides the correct `async_register_static_paths` pattern, `runtime_data` on ConfigEntry, and shared aiohttp session via `async_get_clientsession`. The primary work is replacing the generic `ApiClient` with an arr-specific client, rewriting `config_flow.py` for 3 arr service steps, and updating the coordinator to poll multiple services with partial failure handling.

**Primary recommendation:** Build a single `ArrClient` class parameterized by service type (radarr/sonarr/lidarr) that handles API version differences (/api/v3 vs /api/v1), then wire three instances through the config flow and coordinator.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Each step is one arr service: Radarr -> Sonarr -> Lidarr
- Each step shows URL + API key fields only (no profile/folder selection in config)
- "I don't use this service" skip checkbox per step
- Auto-advance on successful validation (no confirmation toast)
- Inline field errors on validation failure (e.g., "Invalid API key" below the API key field)
- If user skips ALL services, block on the last step (Lidarr) with "At least one service must be configured"
- User enters base URL only (e.g., `http://192.168.1.50:7878`)
- Integration appends `/api/v3/...` or `/api/v1/...` internally
- Support reverse proxy base paths (e.g., `https://media.example.com/radarr`)
- Strip trailing slashes from input
- Placeholder example in URL field (e.g., `http://192.168.1.50:7878`)
- Quality profiles, root folders, and metadata profiles (Lidarr) fetched at config time
- Use the arr service's own default profile as the selected default; fall back to first returned if none marked default
- Profiles stored in config entry data, not re-fetched automatically
- Manual "Refresh profiles" button in options flow for picking up changes
- Config-time: inline field errors (red text below field), user stays on step to fix
- Runtime: mark sensor entity unavailable on poll failure, auto-recover on next success
- 10-second connection timeout for all arr API calls
- SSL certificate verification on by default, per-service toggle to disable (for self-signed certs)
- Options flow: Dropdowns for quality profile, root folder per configured service; metadata profile (Lidarr only); "Verify SSL" toggle per service; "Refresh profiles" button
- Reconfigure flow: Full reconfigure re-runs config wizard with current values pre-filled; only re-validate services whose URL or API key changed
- Single DataUpdateCoordinator for all configured services
- Polls every 5 minutes
- Partial success: if one service fails, update others normally, mark failed service's sensor unavailable

### Claude's Discretion
- Unique_id strategy (hash of first URL, all URLs, or singleton)
- Integration display name ("Requestarr" vs user-configurable)
- Coordinator poll data scope (counts only vs counts + system health)
- Exact error message wording for validation failures
- URL normalization edge cases (double slashes, trailing paths)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONF-01 | User can configure Radarr connection (URL, API key) with live validation via `/api/v3/system/status` | ArrClient with validate_connection() calling /api/v3/system/status; config_flow async_step_radarr |
| CONF-02 | User can configure Sonarr connection (URL, API key) with live validation via `/api/v3/system/status` | Same ArrClient pattern; config_flow async_step_sonarr |
| CONF-03 | User can configure Lidarr connection (URL, API key) with live validation via `/api/v1/system/status` | ArrClient with api_version="v1" parameter; config_flow async_step_lidarr |
| CONF-04 | Each arr service is optional (user can skip) but at least one must be configured | Skip checkbox in schema; accumulate skipped services; validate at least one on final step |
| CONF-05 | Quality profile, root folder, and metadata profile (Lidarr) fetched at config time | After successful validation, fetch /qualityProfile, /rootFolder, /metadataProfile (Lidarr); store in config entry data |
| SENS-04 | Sensors update via DataUpdateCoordinator polling every 5 minutes | Coordinator._async_update_data polls /movie, /series, /artist (or lightweight endpoint) for counts |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | HA-bundled (~3.9.x) | All HTTP calls to arr services | HA's shared session; zero pip deps |
| voluptuous | HA-bundled | Config flow schema validation | HA's standard schema library |
| homeassistant.config_entries.ConfigFlow | HA 2024.1+ | Multi-step config wizard | Required for HACS integrations |
| homeassistant.helpers.update_coordinator.DataUpdateCoordinator | HA 2024.1+ | Polling coordinator | HA's standard polling pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| homeassistant.helpers.aiohttp_client.async_get_clientsession | HA-bundled | Shared aiohttp session | Always — never create own sessions |
| homeassistant.helpers.selector | HA-bundled | Config flow selectors (SelectSelector for dropdowns) | Options flow profile/folder dropdowns |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single ArrClient class | Separate RadarrClient, SonarrClient, LidarrClient classes | More code, more maintenance; services are 95% identical |
| URL string input | vol.Url() validator | vol.Url() rejects IP:port without scheme; str with manual validation is more flexible |

## Architecture Patterns

### Recommended Project Structure
```
custom_components/requestarr/
├── __init__.py          # Wire coordinator + clients into runtime_data
├── api.py               # ArrClient class (uniform for all arr services)
├── config_flow.py       # 3-step wizard + options flow + reconfigure flow
├── const.py             # All constants
├── coordinator.py       # DataUpdateCoordinator polling library counts
├── strings.json         # Config flow UI strings
└── translations/
    └── en.json          # Must mirror strings.json
```

### Pattern 1: Uniform ArrClient with Service Type Parameter
**What:** Single API client class that handles Radarr (v3), Sonarr (v3), and Lidarr (v1) through a `service_type` parameter that controls API version prefix.
**When to use:** All arr API interactions.
**Example:**
```python
class ArrClient:
    """Uniform API client for Radarr, Sonarr, and Lidarr."""

    API_VERSIONS = {
        "radarr": "v3",
        "sonarr": "v3",
        "lidarr": "v1",
    }

    def __init__(
        self,
        base_url: str,
        api_key: str,
        service_type: str,
        session: aiohttp.ClientSession,
        verify_ssl: bool = True,
        timeout: int = 10,
    ) -> None:
        # Strip trailing slashes
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._service_type = service_type
        self._api_version = self.API_VERSIONS[service_type]
        self._session = session
        self._verify_ssl = verify_ssl
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def _api_base(self) -> str:
        return f"{self._base_url}/api/{self._api_version}"

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self._api_key}

    async def async_validate_connection(self) -> bool:
        """Validate connection via /system/status."""
        url = f"{self._api_base}/system/status"
        ssl = None if self._verify_ssl else False
        async with asyncio.timeout(self._timeout.total):
            resp = await self._session.get(
                url, headers=self._headers(), ssl=ssl
            )
        if resp.status in (401, 403):
            raise InvalidAuthError
        if resp.status >= 400:
            raise CannotConnectError(f"HTTP {resp.status}")
        return True
```

### Pattern 2: Config Flow with Skip Checkbox and Accumulated Data
**What:** Each step shows URL + API key + skip checkbox. On skip, advance immediately. On input, validate then advance. Track which services are configured in `self._data`. On the final step (Lidarr), if no services configured yet and user skips, show error.
**When to use:** The 3-step wizard.
**Example:**
```python
async def async_step_radarr(self, user_input=None):
    errors = {}
    if user_input is not None:
        if user_input.get(CONF_SKIP_RADARR):
            return await self.async_step_sonarr()
        # Validate connection...
        if not errors:
            self._data[CONF_RADARR_URL] = user_input[CONF_RADARR_URL]
            self._data[CONF_RADARR_API_KEY] = user_input[CONF_RADARR_API_KEY]
            # Fetch profiles/folders after successful validation
            profiles = await client.async_get_quality_profiles()
            folders = await client.async_get_root_folders()
            self._data[CONF_RADARR_PROFILES] = profiles
            self._data[CONF_RADARR_FOLDERS] = folders
            return await self.async_step_sonarr()
    return self.async_show_form(step_id="radarr", ...)
```

### Pattern 3: Coordinator with Partial Failure Tolerance
**What:** The coordinator builds ArrClient instances for each configured service and polls them independently. If one service fails, the others still update. Failed services are tracked so sensors can mark themselves unavailable.
**When to use:** `_async_update_data` in the coordinator.
**Example:**
```python
async def _async_update_data(self) -> dict[str, Any]:
    data = {}
    errors = {}
    for service_type, client in self._clients.items():
        try:
            count = await client.async_get_library_count()
            data[f"{service_type}_count"] = count
        except (CannotConnectError, InvalidAuthError) as err:
            errors[service_type] = str(err)
            data[f"{service_type}_count"] = None

    if errors and not data:
        # All services failed
        raise UpdateFailed(f"All services unavailable: {errors}")

    data["errors"] = errors
    return data
```

### Anti-Patterns to Avoid
- **Creating new aiohttp sessions:** Use `async_get_clientsession(hass)` — the template already does this correctly
- **Hardcoding quality profile IDs:** Always fetch from the service
- **Storing profiles in hass.data instead of config entry:** Config entry data persists across restarts
- **Validating URL format strictly with vol.Url():** Many users enter IPs without scheme; be lenient and normalize
- **Calling API during form display:** All API calls must be inside `if user_input is not None` guard

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client | Custom aiohttp wrapper with retry/backoff | HA's `async_get_clientsession` + simple error handling | HA manages connection pools; retry is overkill for LAN services |
| Config flow form rendering | Custom HTML/templates | HA's `self.async_show_form(data_schema=...)` | HA renders forms automatically from voluptuous schemas |
| Polling timer | Manual asyncio.create_task with sleep loop | DataUpdateCoordinator | HA manages lifecycle, error handling, and shutdown |
| SSL context management | Custom ssl.SSLContext | aiohttp's `ssl=False` parameter | One parameter vs 10 lines of SSLContext setup |

## Common Pitfalls

### Pitfall 1: Config Flow Skip Logic — Missing "At Least One Required" Check
**What goes wrong:** User skips all three services and config entry is created with no arr services configured. Integration then has nothing to poll and throws errors.
**Why it happens:** Each step independently allows skipping, but no step checks the aggregate state.
**How to avoid:** On the final step (Lidarr), check if any previous service was configured. If not and user tries to skip, return an error: "At least one service must be configured."
**Warning signs:** Config entry created with empty URL/key for all services.

### Pitfall 2: Profile Fetch Fails After Successful Connection Validation
**What goes wrong:** `/system/status` returns 200, so validation passes. But `/qualityProfile` or `/rootFolder` returns 403 because the API key has restricted permissions.
**Why it happens:** Some users create API keys with limited scope in their arr services.
**How to avoid:** Fetch profiles immediately after validation passes, within the same step handler. If profile fetch fails, show an inline error like "Connected but could not fetch profiles — check API key permissions."
**Warning signs:** Config entry created but profiles array is empty or None.

### Pitfall 3: Base URL Normalization Edge Cases
**What goes wrong:** User enters `http://192.168.1.50:7878/` (trailing slash) or `https://media.example.com/radarr/` (trailing slash after base path). Double slashes appear in API URLs: `http://host//api/v3/system/status`.
**Why it happens:** String concatenation without normalization.
**How to avoid:** Strip trailing slashes from user input: `url = user_input[CONF_URL].rstrip("/")`. Do this in the step handler before storing.
**Warning signs:** 404 errors from arr services due to malformed URLs.

### Pitfall 4: SSL Verification Blocks Self-Signed Certificates
**What goes wrong:** User has arr services behind a reverse proxy with a self-signed cert. SSL verification fails and validation returns "cannot connect."
**Why it happens:** aiohttp's default behavior verifies SSL certificates.
**How to avoid:** Add a per-service "Verify SSL" toggle in the config flow. Pass `ssl=False` to aiohttp when disabled. Default to True (secure by default).
**Warning signs:** Users with self-signed certs can't set up the integration.

### Pitfall 5: Options Flow Stale Profile Data
**What goes wrong:** User adds a new quality profile in Radarr after config. Options flow dropdown shows only the old profiles because data was fetched once at config time.
**Why it happens:** Profiles are stored in config entry data and never refreshed.
**How to avoid:** Add a "Refresh profiles" action in the options flow that re-fetches profiles from all configured services and updates the config entry data.
**Warning signs:** Dropdown options don't reflect arr service changes.

## Code Examples

### ArrClient — Full Validation + Profile Fetch
```python
class ArrClient:
    """Uniform API client for Radarr, Sonarr, and Lidarr."""

    API_VERSIONS = {"radarr": "v3", "sonarr": "v3", "lidarr": "v1"}

    LIBRARY_ENDPOINTS = {
        "radarr": "/movie",
        "sonarr": "/series",
        "lidarr": "/artist",
    }

    def __init__(self, base_url, api_key, service_type, session, verify_ssl=True, timeout=10):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._service_type = service_type
        self._api_version = self.API_VERSIONS[service_type]
        self._session = session
        self._ssl = None if verify_ssl else False
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def _api_base(self):
        return f"{self._base_url}/api/{self._api_version}"

    def _headers(self):
        return {"X-Api-Key": self._api_key}

    async def _request(self, method, endpoint, **kwargs):
        url = f"{self._api_base}{endpoint}"
        try:
            resp = await self._session.request(
                method, url,
                headers=self._headers(),
                ssl=self._ssl,
                timeout=self._timeout,
                **kwargs,
            )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnectError(str(err)) from err
        if resp.status in (401, 403):
            raise InvalidAuthError
        if resp.status >= 400:
            raise CannotConnectError(f"HTTP {resp.status}")
        return await resp.json()

    async def async_validate_connection(self):
        await self._request("GET", "/system/status")
        return True

    async def async_get_quality_profiles(self):
        return await self._request("GET", "/qualityprofile")

    async def async_get_root_folders(self):
        return await self._request("GET", "/rootfolder")

    async def async_get_metadata_profiles(self):
        """Lidarr only."""
        return await self._request("GET", "/metadataprofile")

    async def async_get_library_count(self):
        endpoint = self.LIBRARY_ENDPOINTS[self._service_type]
        items = await self._request("GET", endpoint)
        return len(items)
```

### Config Flow — Radarr Step with Skip + Profile Fetch
```python
STEP_RADARR_SCHEMA = vol.Schema({
    vol.Optional(CONF_RADARR_URL, default=""): str,
    vol.Optional(CONF_RADARR_API_KEY, default=""): str,
    vol.Optional(CONF_RADARR_VERIFY_SSL, default=True): bool,
    vol.Optional(CONF_SKIP_RADARR, default=False): bool,
})

async def async_step_radarr(self, user_input=None):
    errors = {}
    if user_input is not None:
        if user_input.get(CONF_SKIP_RADARR):
            return await self.async_step_sonarr()

        url = user_input.get(CONF_RADARR_URL, "").strip().rstrip("/")
        api_key = user_input.get(CONF_RADARR_API_KEY, "").strip()

        if not url:
            errors[CONF_RADARR_URL] = "url_required"
        elif not api_key:
            errors[CONF_RADARR_API_KEY] = "api_key_required"
        else:
            session = async_get_clientsession(self.hass)
            client = ArrClient(url, api_key, "radarr", session,
                             verify_ssl=user_input.get(CONF_RADARR_VERIFY_SSL, True))
            try:
                await client.async_validate_connection()
                profiles = await client.async_get_quality_profiles()
                folders = await client.async_get_root_folders()
            except InvalidAuthError:
                errors[CONF_RADARR_API_KEY] = "invalid_auth"
            except CannotConnectError:
                errors[CONF_RADARR_URL] = "cannot_connect"
            else:
                self._data[CONF_RADARR_URL] = url
                self._data[CONF_RADARR_API_KEY] = api_key
                self._data[CONF_RADARR_VERIFY_SSL] = user_input.get(CONF_RADARR_VERIFY_SSL, True)
                self._data[CONF_RADARR_PROFILES] = [
                    {"id": p["id"], "name": p["name"]} for p in profiles
                ]
                self._data[CONF_RADARR_FOLDERS] = [
                    {"id": f["id"], "path": f["path"]} for f in folders
                ]
                # Select default profile
                default_profile = next(
                    (p for p in profiles if p.get("isDefault")), profiles[0] if profiles else None
                )
                if default_profile:
                    self._data[CONF_RADARR_QUALITY_PROFILE_ID] = default_profile["id"]
                if folders:
                    self._data[CONF_RADARR_ROOT_FOLDER] = folders[0]["path"]
                return await self.async_step_sonarr()

    return self.async_show_form(
        step_id="radarr",
        data_schema=STEP_RADARR_SCHEMA,
        errors=errors,
        description_placeholders={"url_example": "http://192.168.1.50:7878"},
    )
```

### Coordinator — Partial Failure Tolerance
```python
class RequestarrCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, entry):
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.config_entry = entry
        session = async_get_clientsession(hass)
        self._clients: dict[str, ArrClient] = {}

        for service_type in ("radarr", "sonarr", "lidarr"):
            url_key = f"{service_type}_url"
            key_key = f"{service_type}_api_key"
            if entry.data.get(url_key):
                self._clients[service_type] = ArrClient(
                    base_url=entry.data[url_key],
                    api_key=entry.data[key_key],
                    service_type=service_type,
                    session=session,
                    verify_ssl=entry.data.get(f"{service_type}_verify_ssl", True),
                )

    async def _async_update_data(self):
        data = {}
        errors = {}
        for service_type, client in self._clients.items():
            try:
                count = await client.async_get_library_count()
                data[f"{service_type}_count"] = count
            except (CannotConnectError, InvalidAuthError) as err:
                _LOGGER.warning("Failed to poll %s: %s", service_type, err)
                errors[service_type] = str(err)
                data[f"{service_type}_count"] = None

        if not data or all(v is None for k, v in data.items() if k.endswith("_count")):
            raise UpdateFailed(f"All services unavailable: {errors}")

        data["errors"] = errors
        return data
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hass.http.register_static_path` | `async_register_static_paths([StaticPathConfig(...)])` | HA 2024.6 (removed 2025.7) | Template already uses new API |
| `hass.data[DOMAIN][entry_id]` | `entry.runtime_data = TypedData(...)` | HA 2024.x | Template already uses runtime_data |
| `register_static_path` sync | `async_register_static_paths` async | HA 2024.6 | Already fixed in template |

**Deprecated/outdated:**
- `OptionsFlowHandler.__init__(self, config_entry)`: HA 2025.1+ deprecated explicit config_entry in OptionsFlow init. Use `self.config_entry` property instead (available automatically).

## Open Questions

1. **Library count endpoint efficiency**
   - What we know: `/movie`, `/series`, `/artist` endpoints return full arrays. For large libraries (5000+ items) this fetches megabytes of JSON just for a count.
   - What's unclear: Whether arr services have a lightweight count-only endpoint.
   - Recommendation: Use the full array endpoint for now. If performance is an issue, investigate `/api/v3/movie?pageSize=1` with pagination headers, or check if arr services return a `totalRecords` header. This is optimization, not blocking.

2. **Default profile detection**
   - What we know: Quality profiles have an `id` and `name`. Radarr/Sonarr do not have an `isDefault` field on profiles.
   - What's unclear: Whether there's a convention for which profile is "default."
   - Recommendation: Use the first profile in the returned array as the default selection. Users can change in options flow.

3. **Unique ID strategy**
   - What we know: Template uses `f"{host}:{port}"` as unique_id.
   - Recommendation: Use the first configured arr service URL as the unique_id. This prevents duplicate entries while allowing different configurations. Since Requestarr is a singleton per HA instance (one arr stack), a simpler approach is a fixed unique_id like `DOMAIN` itself. This prevents any duplicate entry.

## Sources

### Primary (HIGH confidence)
- HA Developer Docs — Config flow handler: https://developers.home-assistant.io/docs/config_entries_config_flow_handler/
- HA Developer Docs — DataUpdateCoordinator: https://developers.home-assistant.io/docs/integration_fetching_data/
- HA Developer Docs — runtime_data: https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/runtime-data/
- HA Developer Docs — inject-websession: https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/inject-websession/
- Radarr API — system/status, qualityProfile, rootFolder: https://radarr.video/docs/api/
- Sonarr API — system/status, qualityProfile, rootFolder: https://sonarr.tv/docs/api/
- Lidarr API — system/status, qualityProfile, rootFolder, metadataProfile: https://lidarr.audio/docs/api/

### Secondary (MEDIUM confidence)
- Existing project research: `.planning/research/ARR_LOOKUP_API.md`, `ARCHITECTURE.md`, `STACK.md`, `PITFALLS.md`
- Template scaffold analysis: `custom_components/requestarr/` files

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - HA patterns are well-documented, arr APIs are stable
- Architecture: HIGH - Single ArrClient pattern verified against all three arr API versions
- Pitfalls: HIGH - Drawn from project-level pitfalls research and HA developer docs

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable APIs, stable HA patterns)
