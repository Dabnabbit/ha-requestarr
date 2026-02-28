# Phase 5: Library State + Card Polish + Validation - Research

**Researched:** 2026-02-27
**Domain:** Lovelace card editor, "In Library" badge UI, pytest unit testing for HA integrations, CI validation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**In-Library item behavior**
- `id > 0` from arr lookup response = "In Library" — applies to all three media types
- Request button is grayed out and shows "In Library" text when item is in library — not hidden, not clickable
- For TV shows: treat as "In Library" if the show exists (id > 0), regardless of missing seasons/episodes
- For Lidarr: check at artist level only — if artist has id > 0, badge appears; no album-level granularity
- Search results keep original arr relevance order — no re-sorting of in-library items to bottom
- Behavior is consistent across movies, TV shows, and music (same badge, same button treatment)

**Card editor scope**
- Visual editor exposes: service toggles (which tabs to show) + display options only
- Only services that are actually configured in the integration appear as toggleable options in the editor — unconfigured services are not shown
- Editor structure: fields + save button only (no live preview pane)
- Card title/header handling: Claude's discretion

**Badge visual design**
- Green badge (not HA theme color) — universally understood as "available/present"
- Badge is a pill overlay on the poster/thumbnail, consistent across movies, TV, and music results
- Disabled button state: grayed out with "In Library" text (button stays visible to communicate why it can't be clicked)
- Result ordering unchanged — no sorting by library state

**Test strategy**
- Primary goal: pytest unit tests covering logic + eventual hassfest/hacs CI compliance
- Local fallback when GHA hours exhausted: `pytest` from repo root + manual HA reload in dev environment
- Coverage areas (all four required):
  1. Config flow validation — each wizard step, error states, skip logic
  2. Coordinator + API client — polling, ArrClient requests, timeout/error handling
  3. WebSocket commands — search, result normalization, in_library detection, error responses
  4. Request flow — add-to-arr payload building, profile lookup, error handling (Phases 3+4 logic)
- Mock approach: inline mock data in test functions (not JSON fixture files)

### Claude's Discretion
- Card title/header — whether to show one, its default value, and whether it's in the editor
- Badge placement specifics (top-right vs bottom-left on poster)
- Loading skeleton and error state styling
- pytest directory structure and test file naming

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REQT-05 | "Already in library" indicator from arr lookup response (id > 0 means in library) | `in_library` field already normalized and included in all three search result payloads (movies, TV, music). Card already reads `item.in_library` in `_getItemState()`. Need to: add green badge overlay on poster/avatar, replace request button with disabled "In Library" button when `in_library === true`. |
| CARD-05 | Visual card editor for configuration | Requires implementing `RequestarrCardEditor` class (stub exists). Must expose service toggles and dispatch `config-changed` event. Services available in card are readable from `hass.states` by filtering for `requestarr.*` sensor entities. |
</phase_requirements>

## Summary

Phase 5 is a polish and validation phase building on the fully functional Phases 1-4 codebase. The backend already delivers `in_library` in every search result — the work is entirely on the frontend (badge rendering) and test coverage. The card (`requestarr-card.js`) already has `_getItemState()` logic that reads `item.in_library`, but the current render path shows no visual indication when items are already in the library; this needs a green "In Library" badge on the poster/avatar overlay and a disabled button replacing the "Request" button.

The test suite has existing files for all four coverage areas (config flow, coordinator, WebSocket, sensor) but all tests fail because the installed `pytest-homeassistant-custom-component` (0.13.205 / HA 2025.1.4) is incompatible with the integration's `__init__.py`, which imports `async_register_static_paths` from `homeassistant.components.http` — that API was added in HA 2025.7. The tests need to either mock or patch the import, or the package needs upgrading to 0.13.316 (HA 2026.2.3). The existing test file content is substantially scaffold-era code (testing template patterns like `ApiClient`, `TemplateCoordinator`, `get_data` endpoint) rather than Requestarr-specific logic — all four test files must be completely rewritten for Phase 5.

CI is hassfest + hacs/action only (no pytest job in the workflow). HACS CI checks manifest fields, hacs.json, directory structure, and README presence. Hassfest validates manifest.json schema. Both currently pass based on the template scaffold. No new CI jobs are needed.

**Primary recommendation:** Fix the test package version mismatch first (add `--break-system-packages` or use a venv), then completely rewrite all four test files to test Requestarr-specific behavior.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.3.4 (installed) | Test runner | Standard Python test framework |
| pytest-homeassistant-custom-component | 0.13.316 (target) | HA test fixtures, MockConfigEntry, hass_ws_client | The only supported way to unit-test HA custom integrations |
| homeassistant | 2026.2.3 (bundled with 0.13.316) | Integration target | Pinned by the pytest package |
| LitElement (via HA host page) | HA-provided | Card base class | Already used in card via `customElements.get("hui-masonry-view")` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unittest.mock | stdlib | `AsyncMock`, `patch` | Mocking ArrClient methods, async_setup_entry in tests |
| `hass_ws_client` fixture | from pytest-ha-cc | WebSocket test client | Testing WS search/request handlers end-to-end |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest-homeassistant-custom-component | boralyl/pytest-homeassistant | MatthewFlamm's package bundles HA itself; boralyl's approach is more fragile |
| Rewriting tests from scratch | Fixing existing test files | Same outcome — existing files test template patterns, not Requestarr logic |

**Package upgrade command:**
```bash
pip install --user --break-system-packages "pytest-homeassistant-custom-component==0.13.316"
```

**Run tests:**
```bash
cd /home/dab/Projects/ha-requestarr && /home/dab/.local/bin/pytest tests/ -v
```

## Architecture Patterns

### Current Project Structure (confirmed)

```
custom_components/requestarr/
├── __init__.py          # async_setup, async_setup_entry, async_unload_entry
├── api.py               # ArrClient (single class, parameterized by service_type)
├── config_flow.py       # 3-step wizard (Radarr → Sonarr → Lidarr) + options + reconfigure
├── const.py             # All constants
├── coordinator.py       # RequestarrCoordinator (partial-failure, polls library counts)
├── sensor.py            # RequestarrSensor (connected/disconnected/error state)
├── binary_sensor.py     # (template scaffold, currently unused)
├── services.py          # query service (template scaffold)
├── websocket.py         # 7 WS commands: get_data, search_*, request_*
└── frontend/
    └── requestarr-card.js   # LitElement card with stub editor
tests/
├── __init__.py
├── conftest.py          # auto_enable_custom_integrations, mock_setup_entry, mock_config_entry
├── test_config_flow.py  # Scaffold-era tests (MUST REWRITE)
├── test_coordinator.py  # Scaffold-era tests (MUST REWRITE)
├── test_sensor.py       # Scaffold-era tests (MUST REWRITE)
├── test_services.py     # Scaffold-era tests (MUST REWRITE)
└── test_websocket.py    # Scaffold-era tests (MUST REWRITE)
```

### Pattern 1: "In Library" Badge on Poster Overlay

**What:** Green pill badge positioned absolute within the poster/avatar container.
**When to use:** When `item.in_library === true` (or equivalently `item.arr_id !== null`).

The poster-wrap already uses `position: relative; overflow: hidden`. Add a `<span class="badge-in-library">In Library</span>` inside `.poster-wrap` / `.avatar-wrap` that uses absolute positioning.

```javascript
// In _renderResultRow and _renderMusicResultRow
_renderInLibraryBadge(item) {
  if (!item.in_library) return html``;
  return html`<span class="badge-in-library">In Library</span>`;
}
// CSS:
// .badge-in-library {
//   position: absolute;
//   bottom: 4px;
//   left: 0; right: 0;
//   background: #4caf50;  /* hardcoded green per decision */
//   color: white;
//   font-size: 0.6rem;
//   font-weight: 700;
//   text-align: center;
//   padding: 2px 0;
// }
```

**Disabled button for in-library items:**

The `_renderStatus` helper currently returns a Request button for `"not_in_library"` state. The existing `_getItemState()` already returns `"available"` or `"monitored"` for in-library items (both have arr_id > 0), but these states show HA-colored badges, not a disabled "In Library" button. Per decision, ALL in-library items (regardless of has_file) should show a grayed-out disabled button with "In Library" text instead.

**Change:** In `_renderStatus`, merge the `available` and `monitored` cases into a single disabled button:

```javascript
_renderStatus(state, item) {
  // ... existing key calc ...
  if (state === "in_library") {  // rename/merge available+monitored
    return html`<button class="req-btn" disabled>In Library</button>`;
  }
  // ... rest of cases
}
```

This requires updating `_getItemState()` to return `"in_library"` for any item where `item.in_library === true` (regardless of `has_file`), consistent across all three media types.

### Pattern 2: Card Editor with config-changed Event

**What:** `RequestarrCardEditor` LitElement that dispatches `config-changed` to communicate config updates to Lovelace.
**When to use:** When HA opens the visual card editor.

```javascript
class RequestarrCardEditor extends LitElement {
  static get properties() {
    return { hass: {}, config: {} };
  }

  setConfig(config) {
    this.config = { ...config };
  }

  // Detect which services are configured by checking hass.states for
  // requestarr sensor entities (sensor.requestarr_radarr, etc.)
  _isServiceConfigured(service) {
    if (!this.hass) return false;
    return Object.keys(this.hass.states).some(
      (k) => k.startsWith(`sensor.requestarr_${service}`)
    );
  }

  _valueChanged(ev) {
    const newConfig = { ...this.config, [ev.target.configKey]: ev.target.checked };
    const event = new Event("config-changed", { bubbles: true, composed: true });
    event.detail = { config: newConfig };
    this.dispatchEvent(event);
  }

  render() {
    const services = ["radarr", "sonarr", "lidarr"];
    return html`
      ${services
        .filter((s) => this._isServiceConfigured(s))
        .map(
          (s) => html`
            <div>
              <label><input type="checkbox"
                .checked="${this.config[`show_${s}`] !== false}"
                .configKey="${`show_${s}`}"
                @change="${this._valueChanged}"
              /> Show ${s.charAt(0).toUpperCase() + s.slice(1)} tab</label>
            </div>
          `
        )}
    `;
  }
}
```

Source: https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/

### Pattern 3: Rewriting Tests for Requestarr Logic

**What:** Replace scaffold-era test content (which tests `TemplateCoordinator`, `ApiClient.async_get_data`, generic `get_data` WS endpoint) with tests targeting actual Requestarr classes and behaviors.

**Key fixture — minimal Requestarr config entry:**

```python
# In conftest.py — replace existing mock_config_entry fixture
@pytest.fixture
def radarr_only_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_RADARR_URL: "http://192.168.1.50:7878",
            CONF_RADARR_API_KEY: "radarr-test-key",
            CONF_RADARR_VERIFY_SSL: True,
            CONF_RADARR_QUALITY_PROFILE_ID: 1,
            CONF_RADARR_ROOT_FOLDER: "/movies",
            CONF_RADARR_PROFILES: [{"id": 1, "name": "HD-1080p"}],
            CONF_RADARR_FOLDERS: [{"id": 1, "path": "/movies"}],
        },
    )
```

**Key coordinator test pattern (partial failure):**

```python
async def test_coordinator_partial_failure(hass, radarr_sonarr_entry):
    """Radarr fails, Sonarr succeeds — coordinator data still valid."""
    with (
        patch.object(ArrClient, "async_get_library_count",
            side_effect=[CannotConnectError("down"), 42]),
    ):
        coordinator = RequestarrCoordinator(hass, radarr_sonarr_entry)
        await coordinator.async_refresh()
    assert coordinator.data["radarr_count"] is None
    assert coordinator.data["sonarr_count"] == 42
```

**Key WebSocket test pattern:**

```python
async def test_search_movies_in_library_flag(hass, hass_ws_client, radarr_entry):
    """Search results include in_library=True when arr lookup returns id > 0."""
    raw_result = [
        {"id": 42, "title": "Inception", "year": 2010, "tmdbId": 27205,
         "titleSlug": "inception", "hasFile": True, "remotePoster": "https://..."}
    ]
    with patch.object(ArrClient, "async_search", return_value=raw_result):
        assert await hass.config_entries.async_setup(radarr_entry.entry_id)
        await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "requestarr/search_movies", "query": "inception"})
    result = await client.receive_json()

    assert result["success"] is True
    assert result["result"]["results"][0]["in_library"] is True
    assert result["result"]["results"][0]["arr_id"] == 42
```

### Pattern 4: conftest.py Updated for Requestarr

The existing `conftest.py` uses `CONF_HOST`/`CONF_PORT`/`CONF_API_KEY` from HA — these are not the actual Requestarr config keys. All fixtures must use Requestarr-specific constants.

```python
from custom_components.requestarr.const import (
    DOMAIN,
    CONF_RADARR_URL, CONF_RADARR_API_KEY, CONF_RADARR_VERIFY_SSL,
    CONF_RADARR_QUALITY_PROFILE_ID, CONF_RADARR_ROOT_FOLDER,
    CONF_RADARR_PROFILES, CONF_RADARR_FOLDERS,
    # ... etc for sonarr, lidarr
)
```

### Anti-Patterns to Avoid

- **Testing `_renderStatus` state for `available`/`monitored` separately:** Decision says ALL in-library items (movies, TV, music) get the same disabled "In Library" button — no distinction between available and monitored states in the UI.
- **Using `hass.states` entity IDs as the only service detection:** Sensor entity IDs depend on HA's naming sanitization. Use `.startswith("sensor.requestarr_radarr")` rather than exact match.
- **Patching `coordinator.ApiClient.async_get_data`:** This is a template import path. The actual class is `custom_components.requestarr.api.ArrClient` with methods `async_get_library_count` and `async_search`.
- **Window-level fixed positioning for dialog from shadow DOM:** Already addressed in Phase 3 via the overlay div pattern in shadow root.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Card editor form schema | Custom form render loop | `getConfigForm()` schema | HA has a built-in form editor system — but ONLY use if schema selectors cover the need; for service toggle checkboxes, manual render is simpler |
| Service availability detection | WebSocket query to backend | `hass.states` filter by `sensor.requestarr_*` | Sensor entities already reflect configured services; no extra WS command needed |
| Test HA event loop isolation | Custom asyncio test setup | `asyncio_mode = "auto"` in pyproject.toml | Already configured; pytest-ha-cc handles HA event loop correctly |
| CSS badge animations | Custom JS animation | CSS-only `transition` on opacity | Simpler, no JS needed, respects HA's reduced-motion preferences |

**Key insight:** The backend already does the heavy lifting for `in_library` detection — this is a pure UI rendering change with no new Python logic needed.

## Common Pitfalls

### Pitfall 1: Test Package Version Mismatch

**What goes wrong:** `pytest` fails immediately with `ImportError: cannot import name 'async_register_static_paths'` because the installed `homeassistant` package (2025.1.4 from pytest-ha-cc 0.13.205) predates HA 2025.7 when `async_register_static_paths` was added to `homeassistant.components.http`.

**Why it happens:** `pytest-homeassistant-custom-component` bundles a specific HA version. The integration targets HA 2025.7+ but the test environment has HA 2025.1.4.

**How to avoid:** Upgrade to `pytest-homeassistant-custom-component==0.13.316` which bundles HA 2026.2.3. Use `--break-system-packages` since this is a WSL dev environment:
```bash
pip install --user --break-system-packages "pytest-homeassistant-custom-component==0.13.316"
```

**Warning signs:** Any test run that immediately errors in conftest.py with an ImportError (not a test failure).

### Pitfall 2: Existing Test Files Test Template Patterns, Not Requestarr

**What goes wrong:** Tests pass but assert on wrong entities/data. For example, `test_coordinator.py` patches `coordinator.ApiClient.async_get_data` — but the actual coordinator uses `RequestarrCoordinator` (not `TemplateCoordinator`) and calls `ArrClient.async_get_library_count`, not `async_get_data`. Tests would silently pass while not covering actual behavior.

**Why it happens:** Tests were scaffolded from the ha-hacs-template and never updated after Phase 1-4 rework.

**How to avoid:** Completely rewrite all four test files. Reference actual class names from the source code:
- `coordinator.py` → `RequestarrCoordinator` with `_async_update_data`
- `api.py` → `ArrClient` with `async_get_library_count`, `async_search`, `async_request_movie`, etc.
- `config_flow.py` → `RequestarrConfigFlow` with steps `radarr`, `sonarr`, `lidarr`
- `websocket.py` → 7 handlers, WS types like `requestarr/search_movies`

**Warning signs:** Tests mock `ApiClient.async_get_data` or reference `TemplateCoordinator`.

### Pitfall 3: conftest.py Uses Wrong Config Keys

**What goes wrong:** `MockConfigEntry(data={CONF_HOST: ..., CONF_PORT: ..., CONF_API_KEY: ...})` — these are standard HA keys, not Requestarr's service-specific keys (`CONF_RADARR_URL`, `CONF_RADARR_API_KEY`, etc.). Tests that set up config entries with wrong keys will fail to build `ArrClient` instances in the coordinator.

**Why it happens:** Scaffold conftest.py was never updated.

**How to avoid:** Update `conftest.py` to use Requestarr constants. Provide at minimum one fixture per scenario (radarr-only, sonarr-only, lidarr-only, all-three).

### Pitfall 4: Badge Overlay Breaks Poster Aspect Ratio

**What goes wrong:** Adding text inside the poster-wrap causes layout shift if `overflow: hidden` is not set or the badge extends the container height.

**Why it happens:** Absolute positioning requires `position: relative` on the parent and `overflow: hidden` to clip. Both are already set on `.poster-wrap` and `.avatar-wrap`.

**How to avoid:** Keep badge as `position: absolute` within the existing containers. Use `bottom: 0` with full-width stretch rather than arbitrary pixel offsets. Do not add any height to `.poster-wrap`.

### Pitfall 5: Card Editor Service Detection Depends on Entity Naming

**What goes wrong:** Sensor entity IDs are sanitized by HA (spaces → underscores, lowercase). If the sensor `_attr_name = "Radarr"` on a device named "Requestarr", the entity ID may be `sensor.requestarr_radarr` or `sensor.requestarr_radarr_2` on re-setup. Exact matching will fail.

**Why it happens:** HA entity registry name collision handling adds suffixes.

**How to avoid:** Use `startsWith("sensor.requestarr_radarr")` pattern (prefix match) when detecting whether Radarr is configured. Alternatively, expose configured services via a WS query or use the sensor's `state` attribute. The simpler approach is prefix-matching `hass.states`.

### Pitfall 6: `_renderStatus` Key Calculation for Music Items

**What goes wrong:** `_renderStatus` currently calculates `key` using `item.tmdb_id ?? item.tvdb_id` — for music items, both are null, so the key is `"null"`. This means music items never properly show their request state.

**Why it happens:** `_renderStatus` was written for movies/TV; music uses `foreign_artist_id` as the key. Music already has a separate `_renderMusicResultRow` that calls `_renderStatus`, but `_renderStatus` uses the wrong key calculation.

**How to avoid:** Fix `_renderStatus` to handle the music case. Accept `key` as a parameter (already computed correctly in `_getItemState` and `_doRequest`) rather than recomputing it internally, OR add a check for `item.foreign_artist_id`.

### Pitfall 7: CI Workflow Has No pytest Step

**What goes wrong:** Expecting `pytest` to run in CI and block merges. The existing `validate.yml` only runs hassfest and hacs/action — no pytest job.

**Why it happens:** Template scaffold only includes static validation. Adding pytest CI requires a separate job with Python setup, dependency install, and `pytest` invocation.

**How to avoid:** Either add a `tests` job to `validate.yml`, OR rely purely on local `pytest` runs per the CONTEXT.md decision ("Local fallback when GHA hours exhausted"). Per the CONTEXT.md, this is acceptable. Do NOT add a pytest CI job unless explicitly requested — GHA hours may be exhausted.

## Code Examples

### In Library Badge on Poster

```javascript
// Source: phase research - extends existing poster-wrap pattern in requestarr-card.js
_renderResultRow(item) {
  const state = this._getItemState(item);
  const key = item.foreign_artist_id != null
    ? String(item.foreign_artist_id)
    : String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
  const reqErr = this._requestError[key];
  return html`
    <div class="result-row">
      <div class="poster-wrap">
        ${item.poster_url
          ? html`<img class="poster" src="${item.poster_url}" alt=""
              @error="${(e) => { e.target.style.display = "none"; }}" />`
          : ""}
        <div class="poster-placeholder"></div>
        ${item.in_library
          ? html`<span class="badge-in-library">In Library</span>`
          : ""}
      </div>
      <div class="result-info">
        <span class="result-title">${item.title}</span>
        ${item.year ? html`<span class="result-year">${item.year}</span>` : ""}
        ${this._renderStatus(state, key, item)}
        ${reqErr ? html`<span class="req-error">${reqErr}</span>` : ""}
      </div>
    </div>
  `;
}
```

### Disabled "In Library" Button in _renderStatus

```javascript
// Source: phase research - decisions mandate disabled button (not hidden, not badge)
// _getItemState should return "in_library" when item.in_library is true
_getItemState(item) {
  const key = item.foreign_artist_id != null
    ? String(item.foreign_artist_id)
    : String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
  if (this._requesting[key] === "requested") return "requested";
  if (item.in_library) return "in_library";   // changed: was checking has_file
  return "not_in_library";
}

_renderStatus(state, key, item) {
  const isRequesting = this._requesting[key] === "requesting";
  switch (state) {
    case "in_library":
      return html`<button class="req-btn req-btn-disabled" disabled>In Library</button>`;
    case "requested":
      return html`<span class="badge badge-requested">Requested</span>`;
    case "not_in_library":
    default:
      return html`<button class="req-btn" ?disabled="${isRequesting}"
        @click="${() => { this._dialogItem = item; }}">
        ${isRequesting ? "Requesting\u2026" : "Request"}
      </button>`;
  }
}
```

### Card Editor — config-changed dispatch

```javascript
// Source: https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/
_fireConfigChanged(newConfig) {
  const ev = new Event("config-changed", { bubbles: true, composed: true });
  ev.detail = { config: newConfig };
  this.dispatchEvent(ev);
}
```

### pytest — coordinator with Requestarr config keys

```python
# Source: direct reading of custom_components/requestarr/coordinator.py and const.py
from unittest.mock import AsyncMock, patch
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.requestarr.api import CannotConnectError, ArrClient
from custom_components.requestarr.const import (
    DOMAIN,
    CONF_RADARR_URL, CONF_RADARR_API_KEY, CONF_RADARR_VERIFY_SSL,
    CONF_RADARR_QUALITY_PROFILE_ID, CONF_RADARR_ROOT_FOLDER,
    CONF_RADARR_PROFILES, CONF_RADARR_FOLDERS,
)
from custom_components.requestarr.coordinator import RequestarrCoordinator

@pytest.fixture
def radarr_entry():
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_RADARR_URL: "http://192.168.1.50:7878",
            CONF_RADARR_API_KEY: "test-api-key",
            CONF_RADARR_VERIFY_SSL: True,
            CONF_RADARR_QUALITY_PROFILE_ID: 1,
            CONF_RADARR_ROOT_FOLDER: "/movies",
            CONF_RADARR_PROFILES: [{"id": 1, "name": "HD-1080p"}],
            CONF_RADARR_FOLDERS: [{"id": 1, "path": "/movies"}],
        },
    )

async def test_coordinator_update(hass, radarr_entry):
    radarr_entry.add_to_hass(hass)
    with patch.object(ArrClient, "async_get_library_count",
                      new_callable=AsyncMock, return_value=42):
        coordinator = RequestarrCoordinator(hass, radarr_entry)
        await coordinator.async_refresh()
    assert coordinator.data["radarr_count"] == 42
```

### pytest — WS search returns in_library flag

```python
# Source: direct reading of custom_components/requestarr/websocket.py
async def test_search_movies_in_library(hass, hass_ws_client, radarr_entry):
    radarr_entry.add_to_hass(hass)
    raw = [{"id": 42, "title": "Inception", "year": 2010, "tmdbId": 27205,
            "titleSlug": "inception", "hasFile": True,
            "remotePoster": "https://image.tmdb.org/t/p/original/test.jpg"}]
    with patch.object(ArrClient, "async_get_library_count",
                      new_callable=AsyncMock, return_value=1):
        with patch.object(ArrClient, "async_search",
                          new_callable=AsyncMock, return_value=raw):
            assert await hass.config_entries.async_setup(radarr_entry.entry_id)
            await hass.async_block_till_done()
            client = await hass_ws_client(hass)
            await client.send_json({"id": 1, "type": "requestarr/search_movies",
                                    "query": "inception"})
            result = await client.receive_json()
    assert result["success"] is True
    res = result["result"]["results"][0]
    assert res["in_library"] is True
    assert res["arr_id"] == 42
    assert res["poster_url"] == "https://image.tmdb.org/t/p/w300/test.jpg"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Template test stubs (ApiClient, TemplateCoordinator) | Requestarr-specific tests (ArrClient, RequestarrCoordinator) | Phase 5 task | Tests actually verify Requestarr behavior |
| Scaffold `RequestarrCardEditor` (returns empty `html\`\``) | Full editor with service toggles | Phase 5 task | Card passes visual editor detection |
| `_getItemState` returns `available`/`monitored` based on `has_file` | Unified `in_library` state for all in-library items | Phase 5 task | Consistent behavior across all media types |
| `register_static_path` (deprecated HA <2025.7) | `async_register_static_paths` (already implemented) | Phase 1-2 | Already done; test package must match |

**Deprecated/outdated in existing test files:**
- `coordinator.TemplateCoordinator`: replaced by `coordinator.RequestarrCoordinator`
- `coordinator.ApiClient`: replaced by `api.ArrClient`
- `CONF_HOST`, `CONF_PORT`, `CONF_API_KEY` in config entry data: replaced by service-specific keys
- `websocket get_data` as the only WS test: 6 more WS commands exist, none tested

## Validation Architecture

> `workflow.nyquist_validation` is not set in `.planning/config.json` — skipping formal validation architecture section. Test strategy is documented in User Constraints above.

**Practical test commands:**

```bash
# Upgrade test package first (one-time):
pip install --user --break-system-packages "pytest-homeassistant-custom-component==0.13.316"

# Run all tests:
cd /home/dab/Projects/ha-requestarr && /home/dab/.local/bin/pytest tests/ -v

# Run specific test file:
/home/dab/.local/bin/pytest tests/test_websocket.py -v

# Run with stop-on-first-fail:
/home/dab/.local/bin/pytest tests/ -x -v
```

**CI validation (hassfest + hacs/action):** Both pass from the CI workflow at `.github/workflows/validate.yml`. No changes needed to the CI workflow itself.

## Open Questions

1. **`_renderStatus` key parameter refactor scope**
   - What we know: `_renderStatus` recomputes the key internally using `item.tmdb_id ?? item.tvdb_id`, which is wrong for music items (foreign_artist_id). This causes music "In Library" state to not render correctly.
   - What's unclear: Whether to fix by (a) passing `key` as a parameter to `_renderStatus`, or (b) adding a music-case check inside `_renderStatus`.
   - Recommendation: Option (a) — pass `key` as a parameter, since the key is already computed correctly in `_getItemState` and `_doRequest`. This makes `_renderStatus` a pure render function with no key logic.

2. **Card editor title/header field**
   - What we know: CONTEXT.md marks this as Claude's discretion. The existing `getStubConfig()` returns `{ header: "Requestarr" }` and `setConfig` defaults to `header: "Requestarr"`.
   - What's unclear: Whether the header field should appear in the editor.
   - Recommendation: Include a text input for "Card Title" in the editor. Default value is "Requestarr". It is a useful user-facing setting that takes one line in the editor.

3. **pytest-homeassistant-custom-component upgrade method**
   - What we know: `pip install --user --break-system-packages` works on this WSL environment. The latest version is 0.13.316 (HA 2026.2.3).
   - What's unclear: Whether this upgrade is idempotent or will affect other projects on this machine.
   - Recommendation: Proceed with upgrade. If isolation is needed, create a venv in the project directory. For the plan, document both options.

## Sources

### Primary (HIGH confidence)
- Direct code reading: `custom_components/requestarr/frontend/requestarr-card.js` — existing card structure, `_getItemState`, `_renderStatus`, `_renderMusicResultRow`, stub editor
- Direct code reading: `custom_components/requestarr/websocket.py` — `in_library` normalization, all 7 WS handlers
- Direct code reading: `custom_components/requestarr/coordinator.py` — `RequestarrCoordinator` class
- Direct code reading: `tests/` — all 5 test files confirmed to use scaffold patterns
- Direct code reading: `pyproject.toml` — pytest config (`asyncio_mode = "auto"`, `testpaths = ["tests"]`)
- `pip` CLI — confirmed installed versions: pytest 8.3.4, pytest-homeassistant-custom-component 0.13.205, homeassistant 2025.1.4
- [HA Custom Card Developer Docs](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/) — `getConfigElement`, `config-changed` event dispatch pattern

### Secondary (MEDIUM confidence)
- [PyPI pytest-homeassistant-custom-component](https://pypi.org/project/pytest-homeassistant-custom-component/) — confirmed latest version 0.13.316 corresponds to HA 2026.2.3
- [pytest-ha-cc ha_version file](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component/blob/master/ha_version) — tracks HA 2026.2.3
- [HACS Integration requirements](https://www.hacs.xyz/docs/publish/integration/) — README, manifest.json, hacs.json requirements confirmed

### Tertiary (LOW confidence)
- Web search findings on `hass.states` filtering for service detection in card editor — pattern described in community posts, not official docs

## Metadata

**Confidence breakdown:**
- "In Library" badge logic: HIGH — `in_library` field is in every search result payload, card code is fully readable, decision is unambiguous
- Card editor: MEDIUM — `config-changed` event dispatch is official API (HIGH), but service detection via `hass.states` prefix-matching is community pattern (LOW)
- Test rewriting: HIGH — existing test problems are confirmed by running pytest and reading test source
- Package upgrade: HIGH — version numbers confirmed via PyPI and pip
- CI validation (hassfest/hacs): HIGH — workflow file read directly, requirements confirmed from HACS docs

**Research date:** 2026-02-27
**Valid until:** 2026-03-29 (30 days — HA ecosystem is fast-moving but Phase 5 targets are stable)
