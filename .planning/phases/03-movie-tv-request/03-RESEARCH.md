# Phase 3: Movie & TV Request - Research

**Researched:** 2026-02-27
**Domain:** Radarr/Sonarr POST API, HA WebSocket commands, LitElement Lovelace card UI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Request confirmation flow:**
- Tapping "Request" opens a confirm dialog (not one-tap)
- Dialog shows: title, quality profile name, root folder path
- On confirm success: button changes to "Requested" (disabled, visually distinct color)
- On failure: inline error text on the result card, button resets to "Request" for retry

**In-library and status states:**
- Items already in Radarr/Sonarr show a green "In Library" badge — no request button shown
- In-library items appear mixed in search results at natural ranking (not sorted to bottom)
- Four visual states to distinguish:
  - **Available** (green) — in library and downloaded/available
  - **Monitored** (blue) — in library but not fully available (monitoring)
  - **Requested** (yellow) — just added, downloading or pending
  - **Not in library** — shows Request button
- Exact field mapping from arr lookup API response to these four states is Claude's discretion (researcher to investigate available fields)

**Result card layout and content:**
- Vertical list layout: one result per row, poster thumbnail on left, info on right
- Each card shows: 2:3 poster thumbnail, title, year, status badge or request button
- No overview snippet — keep it scannable
- Initial state (no query typed): empty card, just the search box visible
- Empty results state: plain text "No results for [query]"

**Search input behavior:**
- One shared search box at the top of the card (above tabs)
- Tab switch (Movies/TV) immediately shows results for the same query in the other service — no re-typing
- 2-character minimum before search fires
- 300ms debounce (already specified in roadmap)
- Loading indicator: spinner in or directly below the search box; previous results stay visible while new ones load

### Claude's Discretion

- Exact spinner placement and styling
- Color values for the four status badge states (stay consistent with HA design system)
- Confirm dialog layout details (modal vs inline popover)
- Poster placeholder when image URL is missing or fails to load

### Deferred Ideas (OUT OF SCOPE)

- Music/Lidarr tab UI — Phase 4
- Card editor (configurable quality profile / root folder per card) — Phase 5
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REQT-01 | User can request a movie to Radarr with one click (POST `/api/v3/movie` with tmdbId from lookup) | Radarr POST payload documented: tmdbId, qualityProfileId, rootFolderPath, monitored, addOptions |
| REQT-02 | User can request a TV series to Sonarr with one click (POST `/api/v3/series` with tvdbId already in lookup response) | Sonarr POST payload documented: tvdbId, title, qualityProfileId, rootFolderPath, seasons, addOptions |
| REQT-04 | Request uses quality profile and root folder from config (not hardcoded) | Config already stores CONF_RADARR_QUALITY_PROFILE_ID, CONF_RADARR_ROOT_FOLDER, CONF_SONARR_QUALITY_PROFILE_ID, CONF_SONARR_ROOT_FOLDER — read these in request handler |
| CARD-01 | Lovelace card with tabbed interface (Movies / TV / Music) | LitElement tab pattern using reactive properties; Music tab rendered as placeholder in this phase |
| CARD-02 | Search input with 300ms debounce | Vanilla JS setTimeout/clearTimeout debounce; no external library needed |
| CARD-03 | Search results: poster-centric list for Movies/TV (2:3 rectangle) | CSS grid/flex row layout; 60px poster + metadata right; 2:3 achieved via width 60px height 90px |
| CARD-04 | Request button on each result with visual feedback — green/blue/yellow/red status badge system | Four states from arr lookup fields (hasFile, monitored, in_library); HA CSS variables for colors |
</phase_requirements>

---

## Summary

Phase 3 splits into two plans: (1) two WebSocket request commands on the backend and (2) a full Lovelace card rewrite on the frontend. The backend work is low-risk — it follows the same pattern as the existing search commands in `websocket.py`, adding `async_request_movie` and `async_request_series` methods to `ArrClient` that POST to Radarr/Sonarr. The request payload for Radarr requires `tmdbId`, `qualityProfileId`, `rootFolderPath`, `title`, `titleSlug`, and `monitored`; all are present in the lookup response or stored config. For Sonarr, `tvdbId` is already returned by the lookup (no extra API call), plus `qualityProfileId`, `rootFolderPath`, `title`, `titleSlug`, and `seasons` array.

The card rewrite is more complex. The existing `requestarr-card.js` is a scaffold with no real UI. This phase replaces it entirely with a tabbed Movies/TV card (Music tab as placeholder) with shared search input, debounced calls, vertical list with poster + status/button, and a confirm dialog. The card uses `hass.connection.sendMessagePromise` for both search (already exists) and the new request commands. LitElement reactive properties drive all UI state (current tab, query, results, loading, dialog state, per-item request state).

The four status states map to arr lookup response fields: `in_library` (id > 0) combined with `has_file` (for "Available" vs "Monitored") from the normalized result. Items just requested in this session get "Requested" state (yellow) tracked locally in the card — the arr API response on a successful POST confirms the add, so the card updates that result item's state immediately without a re-search.

**Primary recommendation:** Implement `async_request_movie` and `async_request_series` in `ArrClient`, add two WebSocket handlers following the existing `_handle_search` pattern, then rebuild the card as a single LitElement component with reactive state management and HA CSS variable colors.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| LitElement | Via HA internals | Lovelace card base class | Already used in existing card; HA frontend bundles Lit |
| aiohttp | HA-managed | HTTP POST to Radarr/Sonarr | Already used for search; shared session pattern |
| voluptuous | HA-managed | WebSocket command schema validation | Already used for search commands |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| HA websocket_api | Built-in | Register WS commands | All backend WS handlers |
| HA CSS variables | Built-in | Status badge colors | `--success-color`, `--warning-color`, `--error-color`, `--primary-color` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LitElement (from HA globals) | Preact/React | HA bundles Lit, no build step needed |
| Inline confirm dialog | `ha-dialog` element | `ha-dialog` exists but requires shadow DOM piercing; inline approach is simpler for a card |
| Vanilla JS debounce | lodash.debounce | No build tooling; setTimeout pattern is sufficient |

**Installation:** No new packages — this phase uses existing HA internals and the already-installed aiohttp.

---

## Architecture Patterns

### Recommended Project Structure

```
custom_components/requestarr/
├── api.py                   # Add async_request_movie, async_request_series
├── websocket.py             # Add WS_TYPE_REQUEST_MOVIE, WS_TYPE_REQUEST_TV handlers
├── const.py                 # Add WS_TYPE_REQUEST_MOVIE, WS_TYPE_REQUEST_TV constants
└── frontend/
    └── requestarr-card.js   # Full rewrite: tabs, search, results, dialog
```

### Pattern 1: ArrClient Request Methods

**What:** Add `async_request_movie` and `async_request_series` to `ArrClient` in `api.py`. Each method POSTs to the service-specific add endpoint with required fields.

**When to use:** Called from WebSocket handlers after confirm dialog on frontend.

**Radarr POST payload (minimum required + recommended):**
```python
# Source: Radarr GitHub develop branch - MovieController.cs validators
payload = {
    "tmdbId": tmdb_id,
    "title": title,
    "titleSlug": title_slug,
    "qualityProfileId": int(quality_profile_id),
    "rootFolderPath": root_folder_path,
    "monitored": True,
    "minimumAvailability": "released",  # conservative default
    "addOptions": {
        "searchForMovie": True,  # trigger immediate search
    },
}
```

**Sonarr POST payload (minimum required + recommended):**
```python
# Source: Sonarr GitHub develop branch - SeriesController.cs validators
payload = {
    "tvdbId": tvdb_id,
    "title": title,
    "titleSlug": title_slug,
    "qualityProfileId": int(quality_profile_id),
    "rootFolderPath": root_folder_path,
    "monitored": True,
    "seasonFolder": True,
    "seriesType": "standard",
    "seasons": seasons,  # list of {seasonNumber: int, monitored: bool} from lookup
    "addOptions": {
        "searchForMissingEpisodes": True,
        "monitor": "all",
    },
}
```

### Pattern 2: WebSocket Request Handler

**What:** Two handlers following the exact pattern of `_handle_search`. The card sends `{type: "requestarr/request_movie", tmdb_id: ..., title: ..., title_slug: ..., seasons: [...]}`. The handler reads quality_profile_id and root_folder from config, calls `client.async_request_movie(...)`, returns `{success: true}` or `{success: false, error_code: ..., message: ...}`.

**When to use:** Triggered by confirm dialog "Confirm" button tap.

```python
# Source: Pattern follows existing websocket.py _handle_search

@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_REQUEST_MOVIE,
        vol.Required("tmdb_id"): int,
        vol.Required("title"): str,
        vol.Required("title_slug"): str,
    }
)
@websocket_api.async_response
async def websocket_request_movie(hass, connection, msg):
    coordinator = _get_coordinator(hass)
    client = coordinator.get_client(SERVICE_RADARR)
    config_data = _get_config_data(hass)
    quality_profile_id = config_data.get(CONF_RADARR_QUALITY_PROFILE_ID)
    root_folder = config_data.get(CONF_RADARR_ROOT_FOLDER)

    try:
        await client.async_request_movie(
            tmdb_id=msg["tmdb_id"],
            title=msg["title"],
            title_slug=msg["title_slug"],
            quality_profile_id=quality_profile_id,
            root_folder_path=root_folder,
        )
        connection.send_result(msg["id"], {"success": True})
    except DuplicateError as err:
        connection.send_result(msg["id"], {
            "success": False, "error_code": "already_exists", "message": str(err)
        })
    except (CannotConnectError, ServerError) as err:
        connection.send_result(msg["id"], {
            "success": False, "error_code": "service_unavailable", "message": str(err)
        })
```

### Pattern 3: LitElement Card Architecture

**What:** Single class `RequestarrCard extends LitElement` managing all UI state as reactive properties. No sub-components to keep the single-file constraint.

**State properties:**
```javascript
static get properties() {
    return {
        hass: { type: Object },
        config: { type: Object },
        _activeTab: { type: String },    // 'movies' | 'tv'
        _query: { type: String },
        _results: { type: Array },
        _loading: { type: Boolean },
        _dialogItem: { type: Object },   // item pending confirm, or null
        _requesting: { type: Object },   // Map of item key -> 'requesting'|'requested'|'error'
        _requestError: { type: Object }, // Map of item key -> error string
    };
}
```

**Debounce pattern:**
```javascript
_onSearchInput(e) {
    this._query = e.target.value;
    clearTimeout(this._debounceTimer);
    if (this._query.length < 2) {
        this._results = [];
        return;
    }
    this._debounceTimer = setTimeout(() => {
        this._doSearch();
    }, 300);
}
```

**WebSocket search call (already works in Phase 2, card just wraps it):**
```javascript
async _doSearch() {
    const type = this._activeTab === 'movies'
        ? 'requestarr/search_movies'
        : 'requestarr/search_tv';
    this._loading = true;
    try {
        const resp = await this.hass.connection.sendMessagePromise({
            type,
            query: this._query,
        });
        this._results = resp.results || [];
    } catch (err) {
        this._results = [];
    } finally {
        this._loading = false;
    }
}
```

**WebSocket request call:**
```javascript
async _doRequest(item) {
    const key = item.tmdb_id || item.tvdb_id;
    this._requesting = { ...this._requesting, [key]: 'requesting' };
    const type = this._activeTab === 'movies'
        ? 'requestarr/request_movie'
        : 'requestarr/request_series';
    const payload = this._activeTab === 'movies'
        ? { type, tmdb_id: item.tmdb_id, title: item.title, title_slug: item.title_slug }
        : { type, tvdb_id: item.tvdb_id, title: item.title, title_slug: item.title_slug, seasons: item.seasons };
    try {
        const resp = await this.hass.connection.sendMessagePromise(payload);
        if (resp.success) {
            this._requesting = { ...this._requesting, [key]: 'requested' };
        } else {
            this._requesting = { ...this._requesting, [key]: 'error' };
            this._requestError = { ...this._requestError, [key]: resp.message };
        }
    } catch (err) {
        this._requesting = { ...this._requesting, [key]: 'error' };
        this._requestError = { ...this._requestError, [key]: 'Connection error' };
    }
    this._dialogItem = null;
}
```

### Pattern 4: Four Status States from Lookup Response

**What:** Map arr lookup result fields to the four display states.

The normalized result from Phase 2 already includes:
- `in_library: bool` (id > 0)
- `arr_id: int | null`

Phase 3 needs to add `has_file` to the normalized result so the card can distinguish Available vs Monitored. The backend normalizer needs one new field:

**Backend addition to `_normalize_movie_result`:**
```python
"has_file": item.get("hasFile", False),
```

**Backend addition to `_normalize_tv_result`:**
```python
# For Sonarr, check statistics.episodeFileCount > 0
# Note: /series/lookup statistics are all 0 (known Sonarr issue #4942)
# Fall back to: in_library and no reliable has_file signal → treat as Monitored
"has_file": False,  # lookup stats always 0, card shows Monitored for all in-library TV
```

**Frontend state mapping:**
```javascript
_getItemState(item) {
    const key = item.tmdb_id || item.tvdb_id;
    const reqState = this._requesting?.[key];
    if (reqState === 'requested') return 'requested';   // yellow - just requested
    if (!item.in_library) return 'not_in_library';      // show Request button
    if (item.has_file) return 'available';              // green
    return 'monitored';                                 // blue - in library, not downloaded
}
```

**Status badge colors using HA CSS variables:**
```css
.badge-available   { background: var(--success-color, #4CAF50); color: white; }
.badge-monitored   { background: var(--info-color, var(--primary-color, #2196F3)); color: white; }
.badge-requested   { background: var(--warning-color, #FF9800); color: white; }
```

### Anti-Patterns to Avoid

- **Separate tab state for results:** Don't maintain separate results arrays per tab. One `_results` array + re-search on tab switch.
- **Re-fetch on tab switch:** Tab switch should immediately trigger `_doSearch()` with the same `_query` but different `type`. Don't show stale results during the new search.
- **Exposing API keys in card:** Never pass Radarr/Sonarr API keys to the frontend. Quality profile ID and root folder come from config; they are safe metadata (not credentials).
- **Inline seasons param for Sonarr from config:** The seasons list for Sonarr MUST come from the lookup result (already in the normalized response for in-library items). Do not manufacture a seasons list.
- **Using `connection.send_error` for request failures:** Use `send_result` with `{"success": false, ...}` so the JS promise resolves (not rejects) and the card can show the inline error message. `send_error` causes promise rejection, which is harder to differentiate from network errors.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debounce timer | Custom debounce class | `setTimeout` + `clearTimeout` | 5 lines; no library needed for a single input |
| HTTP POST to arr | Custom fetch in frontend | `ArrClient._request()` on backend | API key stays server-side; existing error handling |
| Status color system | Custom color map | HA CSS custom properties (`--success-color`, etc.) | Automatically adapts to user's HA theme; light/dark |
| Confirm dialog | Browser `window.confirm()` | Inline LitElement dialog state | `window.confirm` blocked in shadow DOM contexts |

**Key insight:** The request backend is nearly identical to the search backend. Re-use `_get_coordinator`, `_get_config_data`, and the error wrapping pattern from `_handle_search`. Only the HTTP method (POST vs GET) and payload differ.

---

## Common Pitfalls

### Pitfall 1: Sonarr seasons array missing from POST

**What goes wrong:** POST to `/api/v3/series` without a `seasons` array is accepted by the API but Sonarr may not monitor any episodes, leaving the show perpetually not downloading.

**Why it happens:** `seasons` is not validated as required by the controller, but is essential for monitoring behavior.

**How to avoid:** Always include `seasons` from the lookup response in the POST payload. The Sonarr lookup returns the `seasons` array on the result. Pass it through in the WebSocket message from the card.

**Warning signs:** Series appears in Sonarr but 0 episodes monitored.

### Pitfall 2: Radarr duplicate item error (HTTP 400)

**What goes wrong:** User searches, sees movie "Available" (in_library=True), but the request button is shown due to a bug, and POST returns HTTP 400 with "This movie has already been added".

**Why it happens:** Radarr returns a 400 status with a JSON error body containing the error. The current `_request` method raises `ServerError` for all 4xx responses.

**How to avoid:** Catch `ServerError` in `async_request_movie` and check if the response body contains "already been added" — if so, return a specific `DuplicateError`. Alternatively, map 400 to a separate error type. The card should show "Already in library" not "error".

**Warning signs:** Radarr raises HTTP 400 "This movie has already been added."

### Pitfall 3: Sonarr lookup statistics always 0

**What goes wrong:** Trying to use `statistics.episodeFileCount` from `/series/lookup` response to determine if a show has downloaded episodes — it is always 0 regardless of actual state.

**Why it happens:** Known Sonarr issue #4942: the lookup endpoint does not populate statistics for in-library items.

**How to avoid:** Do not attempt to show "Available" vs "Monitored" distinction for TV shows based on lookup data. All in-library TV shows show "Monitored" (blue) badge. The distinction is only meaningful for movies where `hasFile` IS returned correctly in lookup results.

**Warning signs:** All in-library TV shows appear as "Monitored" — this is correct/expected behavior.

### Pitfall 4: qualityProfileId type mismatch

**What goes wrong:** Config stores `quality_profile_id` as a string (from YAML schema or options flow selector). Radarr/Sonarr validate it as an integer.

**Why it happens:** HTML form `<select>` values are strings; voluptuous schema may store as str.

**How to avoid:** Cast to `int()` before including in POST payload. Already noted in Pattern 2 above (`int(quality_profile_id)`).

**Warning signs:** Radarr returns 422 Unprocessable Entity on POST.

### Pitfall 5: LitElement property mutation not triggering re-render

**What goes wrong:** Mutating `this._requesting[key] = 'requested'` does not trigger re-render because LitElement only detects reference changes for objects.

**Why it happens:** LitElement uses `===` comparison for object properties.

**How to avoid:** Always spread to a new object: `this._requesting = { ...this._requesting, [key]: 'requested' }`. Same for `_requestError`.

**Warning signs:** Button state does not update visually after request completes.

### Pitfall 6: Tab switch search race condition

**What goes wrong:** User switches tabs while previous search is in flight. Old results arrive after the new tab's results and overwrite them.

**Why it happens:** `sendMessagePromise` resolves in arrival order, not request order.

**How to avoid:** Track a `_searchSeq` counter. Increment before each search call; capture value in closure. Only commit results if `_searchSeq` still matches when promise resolves.

**Warning signs:** Search results flash/replace correct results with stale data.

### Pitfall 7: titleSlug not in normalized result

**What goes wrong:** The POST to Radarr requires `titleSlug` (e.g., `"interstellar-157336"`). Phase 2's normalizer does not include it.

**Why it happens:** The normalizer was built for search display, not for request submission.

**How to avoid:** Add `title_slug: item.get("titleSlug", "")` to `_normalize_movie_result` and `_normalize_tv_result` in `websocket.py`. Also pass `seasons: item.get("seasons", [])` for TV. The card sends these fields in the request WS message.

**Warning signs:** Radarr/Sonarr POST returns 422 or adds with empty slug.

---

## Code Examples

Verified patterns from official sources:

### ArrClient POST Method

```python
# Extends existing ArrClient in api.py
# Source: Radarr MovieController.cs validators (github.com/Radarr/Radarr)
async def async_request_movie(
    self,
    tmdb_id: int,
    title: str,
    title_slug: str,
    quality_profile_id: int,
    root_folder_path: str,
) -> dict[str, Any]:
    """Add a movie to Radarr.

    Raises:
        CannotConnectError: Cannot reach Radarr.
        InvalidAuthError: API key rejected.
        ServerError: Non-auth HTTP error (includes duplicate 400).
    """
    payload = {
        "tmdbId": tmdb_id,
        "title": title,
        "titleSlug": title_slug,
        "qualityProfileId": int(quality_profile_id),
        "rootFolderPath": root_folder_path,
        "monitored": True,
        "minimumAvailability": "released",
        "addOptions": {"searchForMovie": True},
    }
    return await self._request("POST", "/movie", json=payload)


async def async_request_series(
    self,
    tvdb_id: int,
    title: str,
    title_slug: str,
    quality_profile_id: int,
    root_folder_path: str,
    seasons: list[dict[str, Any]],
) -> dict[str, Any]:
    """Add a series to Sonarr.

    Raises:
        CannotConnectError: Cannot reach Sonarr.
        InvalidAuthError: API key rejected.
        ServerError: Non-auth HTTP error (includes duplicate 400).
    """
    payload = {
        "tvdbId": tvdb_id,
        "title": title,
        "titleSlug": title_slug,
        "qualityProfileId": int(quality_profile_id),
        "rootFolderPath": root_folder_path,
        "monitored": True,
        "seasonFolder": True,
        "seriesType": "standard",
        "seasons": [
            {"seasonNumber": s.get("seasonNumber", 0), "monitored": True}
            for s in seasons
        ],
        "addOptions": {
            "searchForMissingEpisodes": True,
            "monitor": "all",
        },
    }
    return await self._request("POST", "/series", json=payload)
```

### Card Result Row HTML (LitElement template)

```javascript
// Source: Lovelace LitElement pattern; HA CSS variables for theming
_renderResultRow(item) {
    const state = this._getItemState(item);
    const key = item.tmdb_id || item.tvdb_id;
    const reqErr = this._requestError?.[key];
    return html`
        <div class="result-row">
            <div class="poster-wrap">
                ${item.poster_url
                    ? html`<img class="poster" src="${item.poster_url}" alt=""
                            @error="${(e) => { e.target.style.display='none'; }}">`
                    : html`<div class="poster-placeholder"></div>`}
            </div>
            <div class="result-info">
                <span class="result-title">${item.title}</span>
                <span class="result-year">${item.year || ''}</span>
                ${this._renderStatus(state, item)}
                ${reqErr ? html`<span class="req-error">${reqErr}</span>` : ''}
            </div>
        </div>
    `;
}

_renderStatus(state, item) {
    const key = item.tmdb_id || item.tvdb_id;
    switch (state) {
        case 'available':
            return html`<span class="badge badge-available">Available</span>`;
        case 'monitored':
            return html`<span class="badge badge-monitored">Monitored</span>`;
        case 'requested':
            return html`<span class="badge badge-requested">Requested</span>`;
        default:
            return html`<button class="req-btn"
                @click="${() => { this._dialogItem = item; }}">
                Request</button>`;
    }
}
```

### Confirm Dialog (inline LitElement)

```javascript
// Source: LitElement conditional rendering pattern
_renderDialog() {
    if (!this._dialogItem) return html``;
    const item = this._dialogItem;
    const isRequesting = this._requesting?.[item.tmdb_id || item.tvdb_id] === 'requesting';
    return html`
        <div class="dialog-overlay" @click="${() => { this._dialogItem = null; }}">
            <div class="dialog" @click="${(e) => e.stopPropagation()}">
                <div class="dialog-title">${item.title}</div>
                <div class="dialog-meta">
                    <span>Profile: ${item.quality_profile}</span>
                    <span>Folder: ${item.root_folder}</span>
                </div>
                <div class="dialog-actions">
                    <button class="btn-cancel"
                        @click="${() => { this._dialogItem = null; }}">Cancel</button>
                    <button class="btn-confirm"
                        ?disabled="${isRequesting}"
                        @click="${() => this._doRequest(item)}">
                        ${isRequesting ? 'Requesting...' : 'Confirm'}
                    </button>
                </div>
            </div>
        </div>
    `;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Browser `confirm()` dialog | Inline LitElement dialog rendered in shadow DOM | Standard since Lit 2.x | `window.confirm` doesn't work inside shadow DOM reliably |
| `hass.callService()` for backend calls | `hass.connection.sendMessagePromise()` for data-returning WS commands | HA 2022+ | sendMessagePromise gives structured response with result data |
| Separate arr client per service | Single `ArrClient` with service_type param | Phase 1 decision | Same POST pattern works for Radarr and Sonarr; method name differs |

**Deprecated/outdated:**
- `customElements.get("hui-masonry-view")` for LitElement base: Still works as of HA 2025.x. The existing card uses this. Continue using it — no change needed.
- Storing `quality_profile_id` as string: Cast to `int()` before POST. This is a known footgun with HA options flow selectors.

---

## Open Questions

1. **Radarr 400 error body access in `_request`**
   - What we know: `_request` raises `ServerError` for all 4xx, discarding the response body
   - What's unclear: Can we read the error body to distinguish "already added" from other 400s?
   - Recommendation: Modify `async_request_movie` / `async_request_series` to catch `ServerError` and return a structured error to the WS handler; don't need to parse the body — HTTP 400 from Radarr's add endpoint reliably means "duplicate". Map 400 → `already_exists` error code.

2. **Sonarr seasons list from lookup for new (not-in-library) items**
   - What we know: Sonarr lookup returns `seasons` array for in-library items. For items NOT in library (id=0), the seasons list reflects known seasons from TVDB.
   - What's unclear: Are all seasons present in the lookup result for a new show? Are they reliably marked monitored=false?
   - Recommendation: Include all seasons from the lookup response in the POST with `monitored: true`. The `addOptions.monitor: "all"` directive also sets this. If `seasons` is empty in lookup, send an empty array and let Sonarr default behavior apply.

3. **titleSlug uniqueness for Radarr**
   - What we know: `titleSlug` follows the pattern `{clean-title}-{tmdbId}` (e.g., `"interstellar-157336"`)
   - What's unclear: Is it safe to pass the `titleSlug` directly from the lookup result, or does Radarr validate it strictly?
   - Recommendation: Pass the `titleSlug` from the lookup response as-is. Radarr generates and returns it; it will be valid. Add to normalized result in Phase 3 Wave 1.

---

## Sources

### Primary (HIGH confidence)

- `github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/Movies/MovieController.cs` — POST validator requirements verified
- `github.com/Sonarr/Sonarr/blob/develop/src/Sonarr.Api.V3/Series/SeriesController.cs` — POST validator requirements verified
- `github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/Movies/MovieResource.cs` — `hasFile`, `isAvailable`, `monitored`, `titleSlug` fields verified
- `developers.home-assistant.io/docs/frontend/extending/websocket-api/` — `sendMessagePromise` pattern confirmed
- Existing `websocket.py` (Phase 2) — search handler pattern directly reusable for request handlers
- Existing `api.py` (Phase 1/2) — `_request` method accepts `json=` kwarg for POST bodies
- `github.com/Sonarr/Sonarr/issues/4942` — confirmed: lookup statistics always 0 for in-library items

### Secondary (MEDIUM confidence)

- `forums.sonarr.tv/t/v3-api-add-series-request-example/33393` — Sonarr POST example with seasons array verified against controller source
- `gist.github.com/KipK/3cf706ac89573432803aaa2f5ca40492` — HA embedded card developer guide; sendMessagePromise async/await pattern
- `community.home-assistant.io` HA CSS variable list — `--success-color`, `--warning-color`, `--error-color` confirmed as used variables in HA source

### Tertiary (LOW confidence)

- WebSearch: Radarr `minimumAvailability` default value "released" — not verified against official docs; treat as reasonable default

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing Phase 1/2 code directly extended; no new frameworks
- Architecture: HIGH — WebSocket pattern verified against existing working code; arr API payloads verified against source
- Pitfalls: HIGH — Sonarr statistics issue verified against GitHub issue; LitElement mutation pattern is well-known; others derived from API source
- Status state mapping: MEDIUM — `hasFile` field presence in lookup results verified for Radarr; Sonarr statistics=0 verified; TV "Monitored" fallback is pragmatic

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (arr APIs are stable; HA Lovelace patterns change slowly)
