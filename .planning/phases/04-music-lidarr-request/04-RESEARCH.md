# Phase 4: Music + Lidarr Request - Research

**Researched:** 2026-02-27
**Domain:** Lidarr POST API, HA WebSocket commands, LitElement circular avatar UI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Circular avatar presentation:**
- Shape is locked (circular, Spotify convention — already in roadmap)
- Size: Claude's discretion — should match the row height of movie/TV rows (~60px diameter)
- Initials placeholder: first letter of artist name only (e.g. "T" for Taylor Swift, "M" for Metallica)
- Placeholder color: hash the artist name to pick deterministically from a fixed palette (Claude picks tasteful 8-12 color palette); same artist always gets the same color

**Artist result card content:**
- Show: circular avatar + artist name only (no genre tags, no album count, no "year")
- Layout: same vertical list as Movies/TV — one row per result, avatar left, info right
- Initial state (no query): empty card, just the search box (parity with Phase 3)
- Empty results: plain text "No results for [query]" (parity with Phase 3)

**Request confirm dialog:**
- Dialog shows: artist name + quality profile name + metadata profile name + root folder path
- Flow is identical to Phase 3: tap Request → confirm dialog → Confirm → button becomes "Requested"
- On success: button changes to "Requested" (disabled, yellow — parity with Phase 3)
- On failure: inline error text on result row, button resets to "Request" (parity with Phase 3)

**Library states and badge system:**
- Reuse Phase 3's four-state system: Available (green) / Monitored (blue) / Requested (yellow) / Request button
- "Requested" state is in-memory per search session — resets on new search (Phase 5 adds persistent arr library badges)
- State mapping from Lidarr lookup response follows same logic as Phase 3 (researcher to verify Lidarr's `has_file` / `statistics` fields)

### Claude's Discretion

- Avatar diameter (must feel proportionally consistent with 60×90 movie poster rows)
- Exact color palette for initials placeholders
- Whether `_getItemState()` in requestarr-card.js can be shared/extended for music vs. duplicated

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRCH-03 | User can search for music artists via Lidarr lookup endpoint (`/api/v1/artist/lookup`) through WebSocket command | Already implemented in Phase 2 (`websocket_search_music`). Phase 4 activates the card tab to use it. |
| REQT-03 | User can request a music artist to Lidarr with one click (POST `/api/v1/artist` with foreignArtistId from lookup) | Lidarr POST payload: foreignArtistId, qualityProfileId, metadataProfileId, rootFolderPath, monitored, addOptions |
</phase_requirements>

---

## Summary

Phase 4 is the smallest implementation phase of the v1 milestone. It has two deliverables: (1) a `request_artist` WebSocket command on the backend that POSTs to Lidarr, and (2) activating the Music tab in `requestarr-card.js` with circular artist avatars.

The backend work is minimal. The `search_music` WS command and `_normalize_music_result` already exist from Phase 2. The only new backend code is `async_request_artist` on `ArrClient` (same POST pattern as `async_request_movie`/`async_request_series`) and the `websocket_request_artist` handler. The key Lidarr-specific difference is that the POST requires `foreignArtistId` (not tmdbId/tvdbId) and additionally requires `metadataProfileId` — which is already stored in config as `CONF_LIDARR_METADATA_PROFILE_ID`.

The frontend work is a targeted extension of the existing card: remove the disabled state from the Music tab, add `search_music` support to `_doSearch()`, add `request_artist` to `_doRequest()`, and add a `_renderMusicResultRow()` (or extend `_renderResultRow()`) that shows a circular avatar instead of a 2:3 poster. The initials placeholder with deterministic color hashing is purely CSS + a few lines of JS.

The Lidarr artist "in library" state mapping: `id > 0` in the lookup response means in-library (same as Radarr/Sonarr). For "Available" vs "Monitored", Lidarr tracks `statistics.trackFileCount > 0` on the artist — but lookup results have the same limitation as Sonarr: statistics may not be populated. Conservative approach: treat all in-library artists as "Monitored" (blue) in lookup results, same pattern as Phase 3 TV.

**Primary recommendation:** Implement `async_request_artist` in `ArrClient`, add `websocket_request_artist` handler following the exact pattern of `websocket_request_movie`/`websocket_request_series`, extend the card with circular avatar music rows, and activate the Music tab.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| LitElement | Via HA internals | Lovelace card base class | Already used in existing card; HA frontend bundles Lit |
| aiohttp | HA-managed | HTTP POST to Lidarr | Already used for search; shared session pattern |
| voluptuous | HA-managed | WebSocket command schema validation | Already used for all existing commands |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| HA websocket_api | Built-in | Register WS commands | All backend WS handlers |
| HA CSS variables | Built-in | Status badge and avatar colors | `--primary-color`, `--success-color`, etc. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS border-radius: 50% | SVG circle clip | CSS is simpler; same visual result |
| JS string hash for color | Random color | Deterministic = same artist always gets same color across sessions |
| Separate `_renderMusicResultRow` | Modify `_renderResultRow` with tab check | Separate function is cleaner — music and movie/TV rows are visually different |

**Installation:** No new packages — this phase uses existing HA internals and the already-installed aiohttp.

---

## Architecture Patterns

### Recommended Project Structure

```
custom_components/requestarr/
├── const.py          # Add WS_TYPE_REQUEST_ARTIST
├── api.py            # Add async_request_artist
└── websocket.py      # Add websocket_request_artist handler + registration
frontend/
└── requestarr-card.js  # Activate Music tab, add circular avatar renderer, extend _doSearch/_doRequest
```

### Pattern 1: Lidarr POST Artist Payload

**What:** Lidarr `POST /api/v1/artist` adds an artist. Minimum required fields verified from Lidarr source.

**Lidarr POST payload (minimum required + recommended):**
```python
# Source: Lidarr GitHub develop branch - ArtistController.cs
payload = {
    "foreignArtistId": foreign_artist_id,  # MusicBrainz artist GUID (string)
    "qualityProfileId": int(quality_profile_id),
    "metadataProfileId": int(metadata_profile_id),
    "rootFolderPath": root_folder_path,
    "monitored": True,
    "addOptions": {
        "searchForMissingAlbums": True,   # trigger immediate album search
        "monitor": "all",                  # monitor all albums
    },
}
```

**Key Lidarr-specific fields:**
- `foreignArtistId` — string (MusicBrainz GUID). Already in normalized result as `foreign_artist_id`. This is the Lidarr equivalent of `tmdbId`/`tvdbId`.
- `metadataProfileId` — int. Required by Lidarr (no equivalent in Radarr/Sonarr). Already stored in config as `CONF_LIDARR_METADATA_PROFILE_ID`.
- No `titleSlug` — Lidarr does not use titleSlug in the add endpoint (unlike Radarr/Sonarr).
- No `title` required in POST body (Lidarr fetches artist metadata from MusicBrainz via foreignArtistId).

**Duplicate detection:** Lidarr returns HTTP 400 for duplicate adds (same as Radarr/Sonarr). Map `ServerError` with "400" in message → `error_code: "already_exists"`.

### Pattern 2: Artist State Mapping from Lidarr Lookup

**Lidarr lookup result fields relevant to state:**
- `id` > 0 → artist is in library (`in_library = True`)
- `statistics.trackFileCount` — number of downloaded track files. Available in full artist response, NOT reliably populated in lookup results.

**Conservative approach (same as Sonarr TV):**
- All in-library artists → "Monitored" (blue) badge
- Never show "Available" for music from lookup results
- Phase 5 will add persistent library state with proper statistics

**State key for music items:** Use `foreign_artist_id` (string) as the key for `_requesting` and `_requestError` maps in the card. This is the unique identifier returned in the music search results.

### Pattern 3: Circular Avatar CSS

**What:** CSS `border-radius: 50%` on a fixed-size container creates circles. Same absolute-positioning pattern as existing poster-wrap.

```css
/* Avatar (circular) — music tab */
.avatar-wrap {
  position: relative;
  flex-shrink: 0;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--secondary-background-color);
}
.avatar {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}
.avatar-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 1.4rem;
  font-weight: 700;
  color: white;
  /* background-color set inline via style binding */
}
```

**Why 60px diameter:** The existing movie poster is 60×90px. A 60px circle visually balances the row height while centering correctly with `align-items: center` (vs `flex-start` for posters). The row height for music can use `align-items: center` instead of `flex-start`.

### Pattern 4: Deterministic Color Hash for Initials Placeholder

**What:** Hash the artist name to a stable index into a fixed palette. No randomness — same artist name always yields the same color.

```javascript
_hashColor(name) {
  // Simple djb2-style hash
  let h = 5381;
  for (let i = 0; i < name.length; i++) {
    h = ((h << 5) + h) ^ name.charCodeAt(i);
    h = h >>> 0; // force unsigned 32-bit
  }
  const palette = [
    '#E57373', // soft red
    '#F06292', // soft pink
    '#BA68C8', // soft purple
    '#7986CB', // soft indigo
    '#4FC3F7', // soft blue
    '#4DB6AC', // soft teal
    '#81C784', // soft green
    '#FFD54F', // soft amber
    '#FF8A65', // soft deep orange
    '#A1887F', // soft brown
  ];
  return palette[h % palette.length];
}
```

**Palette design choices:** 10 colors, mid-brightness tones that read well in both light and dark HA themes. Avoids pure bright primary colors that would clash with HA's primary-color accents.

### Anti-Patterns to Avoid

- **Sending `title` in Lidarr POST body:** Lidarr does not require `title` in the artist POST (unlike Radarr/Sonarr). Include only `foreignArtistId`, profiles, root folder, `monitored`, `addOptions`.
- **Using `int(foreign_artist_id)`:** `foreignArtistId` is a string GUID (e.g., `"5f9c3f52-3d52-4571-9f8b-..."`). Do NOT cast to int.
- **Sharing poster CSS class with music:** Create `.avatar-wrap` / `.avatar` separate CSS classes. Do not reuse `.poster-wrap` / `.poster` — the shapes differ.
- **Storing `metadataProfileId` inline in the WS message:** The metadata profile ID comes from config, not from the card. The card sends only `foreign_artist_id` + `title`; the backend reads profiles from config.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP POST to Lidarr | Custom fetch in frontend | `ArrClient._request()` on backend | API key stays server-side; existing error handling |
| Color determinism | Random seed | djb2 string hash → palette index | 8 lines; no library; stable across sessions |
| Confirm dialog | New component | Same inline LitElement dialog from Phase 3 | Already implemented; extend `_renderDialog()` to show metadata profile |
| Circular image | SVG clipPath | CSS `border-radius: 50%` + `overflow: hidden` | Simpler; works in all modern browsers |

**Key insight:** The request backend for Lidarr is nearly identical to the movie backend. The only structural differences are: (1) `foreignArtistId` instead of `tmdbId`, (2) an additional `metadataProfileId` parameter, (3) no `titleSlug` in the POST body. Reuse all existing error handling patterns.

---

## Common Pitfalls

### Pitfall 1: metadataProfileId is REQUIRED for Lidarr

**What goes wrong:** POST to `/api/v1/artist` without `metadataProfileId` returns HTTP 422 "metadataProfileId is required".

**Why it happens:** Lidarr has metadata profiles (not present in Radarr/Sonarr) that determine what album types to track. The field is not optional.

**How to avoid:** Always include `metadataProfileId: int(metadata_profile_id)` in the payload. Read from `config_data.get(CONF_LIDARR_METADATA_PROFILE_ID)`. Cast to int (same reason as qualityProfileId — options flow stores as string).

**Warning signs:** Lidarr returns 422 Unprocessable Entity.

### Pitfall 2: foreignArtistId is a STRING, not an integer

**What goes wrong:** Passing `foreignArtistId` as an integer (or casting with `int()`) causes Lidarr to reject the request.

**Why it happens:** `foreignArtistId` is a MusicBrainz GUID (UUID format string), not an integer. Unlike `tmdbId` and `tvdbId` which are integers, this is a string.

**How to avoid:** Pass `foreignArtistId` as-is from the normalized result. Do not cast. In the WS schema, validate as `str`, not `int`.

**Warning signs:** Lidarr returns 400 or 422; Python raises `ValueError` on `int()` cast of a UUID.

### Pitfall 3: Lidarr duplicate returns HTTP 400

**What goes wrong:** User requests an artist already in Lidarr and gets an unhandled error.

**Why it happens:** Same behavior as Radarr/Sonarr — Lidarr returns HTTP 400 for duplicate adds.

**How to avoid:** Same pattern as Phase 3: catch `ServerError`, check if "400" in the error string, return `error_code: "already_exists"` via `send_result` (not `send_error`).

**Warning signs:** Error displays as "service_unavailable" instead of "already_exists".

### Pitfall 4: Music result key collision with movies/TV in `_requesting` map

**What goes wrong:** `foreign_artist_id` is a UUID string (e.g. `"5f9c3f52-..."`). Using `item.tmdb_id ?? item.tvdb_id ?? item.foreign_artist_id` for the key works only if the first two are null for music results. If `item.tmdb_id` is accidentally non-null, the key will collide with a movie result.

**Why it happens:** The normalized music result from Phase 2 does not include `tmdb_id` or `tvdb_id`. They will be `undefined` in JS. `undefined ?? item.foreign_artist_id` correctly falls through to `foreign_artist_id`.

**How to avoid:** In the card, use `item.foreign_artist_id` directly for music items when constructing the key. Extend `_getItemState` and `_renderStatus` to handle the music case.

**Warning signs:** Clicking Request on a music result does nothing or shows the wrong state.

### Pitfall 5: Avatar alignment with row height

**What goes wrong:** 60×60px circle in a flex row with `align-items: flex-start` (the current movie row setting) makes the avatar align to the top, looking off-center against the artist name.

**Why it happens:** Music rows have less text than movie rows (no year field), making the row shorter. Top-alignment looks wrong.

**How to avoid:** Music result rows should use `align-items: center` (not `flex-start`). Either add a `.music-result-row` variant or add a conditional class on the row.

**Warning signs:** Circle avatar appears vertically offset from the artist name text.

### Pitfall 6: img onerror does not hide circular avatar properly

**What goes wrong:** When the fanart.tv image fails to load, the broken `<img>` overlays the initials placeholder.

**Why it happens:** Same mechanism as posters — the `<img>` needs to be hidden on error so the `.avatar-placeholder` behind it is visible.

**How to avoid:** Same `@error` handler: `(e) => { e.target.style.display = 'none'; }`. The placeholder div renders behind the img at all times. Both are inside the circular clip container.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Lidarr Request (api.py addition)

```python
# Extends ArrClient in api.py — same pattern as async_request_movie/async_request_series
# Source: Lidarr GitHub develop branch ArtistController.cs
async def async_request_artist(
    self,
    foreign_artist_id: str,          # MusicBrainz GUID — string, not int
    quality_profile_id: int,
    metadata_profile_id: int,         # Lidarr-specific — no equivalent in Radarr/Sonarr
    root_folder_path: str,
) -> dict[str, Any]:
    """Add an artist to Lidarr.

    Raises:
        CannotConnectError: Cannot reach Lidarr.
        InvalidAuthError: API key rejected.
        ServerError: Non-auth HTTP error. HTTP 400 means artist already exists.
    """
    payload = {
        "foreignArtistId": foreign_artist_id,   # string GUID — DO NOT cast to int
        "qualityProfileId": int(quality_profile_id),
        "metadataProfileId": int(metadata_profile_id),
        "rootFolderPath": root_folder_path,
        "monitored": True,
        "addOptions": {
            "searchForMissingAlbums": True,
            "monitor": "all",
        },
    }
    return await self._request("POST", "/artist", json=payload)
```

### WebSocket Handler (websocket.py addition)

```python
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_REQUEST_ARTIST,
        vol.Required("foreign_artist_id"): str,   # UUID string
        vol.Required("title"): str,                # artist name for display
    }
)
@websocket_api.async_response
async def websocket_request_artist(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle music artist request via Lidarr POST."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_result(
            msg["id"],
            {"success": False, "error_code": "not_configured", "message": "Requestarr not configured"},
        )
        return

    client = coordinator.get_client(SERVICE_LIDARR)
    if client is None:
        connection.send_result(
            msg["id"],
            {"success": False, "error_code": "service_not_configured", "message": "Lidarr is not configured"},
        )
        return

    config_data = _get_config_data(hass)
    quality_profile_id = config_data.get(CONF_LIDARR_QUALITY_PROFILE_ID)
    metadata_profile_id = config_data.get(CONF_LIDARR_METADATA_PROFILE_ID)
    root_folder = config_data.get(CONF_LIDARR_ROOT_FOLDER, "")

    try:
        await client.async_request_artist(
            foreign_artist_id=msg["foreign_artist_id"],
            quality_profile_id=quality_profile_id,
            metadata_profile_id=metadata_profile_id,
            root_folder_path=root_folder,
        )
        connection.send_result(msg["id"], {"success": True})
    except ServerError as err:
        err_str = str(err)
        if "400" in err_str:
            connection.send_result(
                msg["id"],
                {"success": False, "error_code": "already_exists", "message": "This artist is already in Lidarr"},
            )
        else:
            _LOGGER.warning("Artist request failed: %s", err)
            connection.send_result(
                msg["id"],
                {"success": False, "error_code": "service_unavailable", "message": str(err)},
            )
    except (CannotConnectError, InvalidAuthError) as err:
        _LOGGER.warning("Artist request failed: %s", err)
        connection.send_result(
            msg["id"],
            {"success": False, "error_code": "service_unavailable", "message": str(err)},
        )
```

### Music Tab Activation in _doSearch (card JS)

```javascript
async _doSearch() {
    const type =
        this._activeTab === 'movies' ? 'requestarr/search_movies' :
        this._activeTab === 'tv'     ? 'requestarr/search_tv'     :
                                       'requestarr/search_music';
    const seq = ++this._searchSeq;
    this._loading = true;
    try {
        const resp = await this.hass.connection.sendMessagePromise({ type, query: this._query });
        if (seq !== this._searchSeq) return;
        this._results = resp.results || [];
    } catch (_err) {
        if (seq !== this._searchSeq) return;
        this._results = [];
    } finally {
        if (seq === this._searchSeq) this._loading = false;
    }
}
```

### _doRequest Extended for Music (card JS)

```javascript
async _doRequest(item) {
    const key = this._activeTab === 'music'
        ? String(item.foreign_artist_id)
        : String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
    this._requesting = { ...this._requesting, [key]: 'requesting' };
    this._dialogItem = null;

    let payload;
    if (this._activeTab === 'movies') {
        payload = {
            type: 'requestarr/request_movie',
            tmdb_id: item.tmdb_id,
            title: item.title,
            title_slug: item.title_slug,
        };
    } else if (this._activeTab === 'tv') {
        payload = {
            type: 'requestarr/request_series',
            tvdb_id: item.tvdb_id,
            title: item.title,
            title_slug: item.title_slug,
            seasons: item.seasons || [],
        };
    } else {
        payload = {
            type: 'requestarr/request_artist',
            foreign_artist_id: item.foreign_artist_id,
            title: item.title,
        };
    }

    try {
        const resp = await this.hass.connection.sendMessagePromise(payload);
        if (resp.success) {
            this._requesting = { ...this._requesting, [key]: 'requested' };
        } else {
            this._requesting = { ...this._requesting, [key]: 'error' };
            this._requestError = { ...this._requestError, [key]: resp.message || 'Request failed' };
        }
    } catch (_err) {
        this._requesting = { ...this._requesting, [key]: 'error' };
        this._requestError = { ...this._requestError, [key]: 'Connection error' };
    }
}
```

### Circular Avatar Row HTML

```javascript
_renderMusicResultRow(item) {
    const key = String(item.foreign_artist_id);
    const state = this._getMusicItemState(item, key);
    const reqErr = this._requestError[key];
    const initial = item.title ? item.title[0].toUpperCase() : '?';
    const color = this._hashColor(item.title || '');

    return html`
        <div class="result-row music-result-row">
            <div class="avatar-wrap">
                ${item.poster_url
                    ? html`<img class="avatar" src="${item.poster_url}" alt=""
                            @error="${(e) => { e.target.style.display = 'none'; }}">`
                    : ''}
                <div class="avatar-placeholder" style="background-color: ${color}">
                    ${initial}
                </div>
            </div>
            <div class="result-info">
                <span class="result-title">${item.title}</span>
                ${this._renderStatus(state, item)}
                ${reqErr ? html`<span class="req-error">${reqErr}</span>` : ''}
            </div>
        </div>
    `;
}
```

**Note on avatar-placeholder always rendered:** Unlike the poster pattern where placeholder is a div with no content, the avatar-placeholder must always render (it's the fallback). The `<img>` overlaps it when loaded; `@error` hides the img so the placeholder shows through. The placeholder contains the initial letter.

### Confirm Dialog Extended for Music (metadata profile line)

```javascript
_renderDialog() {
    if (!this._dialogItem) return html``;
    const item = this._dialogItem;
    const key = this._activeTab === 'music'
        ? String(item.foreign_artist_id)
        : String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
    const isRequesting = this._requesting[key] === 'requesting';
    return html`
        <div class="dialog-overlay" @click="${() => { this._dialogItem = null; }}">
            <div class="dialog" @click="${(e) => e.stopPropagation()}">
                <div class="dialog-title">${item.title}</div>
                <div class="dialog-meta">
                    <div>Profile: ${item.quality_profile || '\u2014'}</div>
                    ${this._activeTab === 'music' && item.metadata_profile
                        ? html`<div>Metadata: ${item.metadata_profile}</div>`
                        : ''}
                    <div>Folder: ${item.root_folder || '\u2014'}</div>
                </div>
                <div class="dialog-actions">
                    <button class="btn-cancel"
                        @click="${() => { this._dialogItem = null; }}">Cancel</button>
                    <button class="btn-confirm"
                        ?disabled="${isRequesting}"
                        @click="${() => this._doRequest(item)}">
                        ${isRequesting ? 'Requesting\u2026' : 'Confirm'}
                    </button>
                </div>
            </div>
        </div>
    `;
}
```

### Normalizer Extension for metadata_profile (websocket.py)

```python
# Add metadata_profile to _normalize_music_result
# Resolve from CONF_LIDARR_METADATA_PROFILES using same _resolve_profile_name helper

def _normalize_music_result(
    item: dict[str, Any], config_data: dict[str, Any]
) -> dict[str, Any]:
    """Normalize a Lidarr artist lookup result into a standard search result."""
    poster_url = _extract_poster_url(item)
    arr_id = item.get("id", 0)

    return {
        "title": item.get("artistName", ""),
        "year": None,
        "overview": item.get("overview", ""),
        "poster_url": poster_url,
        "in_library": arr_id > 0,
        "arr_id": arr_id if arr_id > 0 else None,
        "foreign_artist_id": item.get("foreignArtistId"),
        "quality_profile": _resolve_profile_name(
            config_data.get(CONF_LIDARR_PROFILES, []),
            config_data.get(CONF_LIDARR_QUALITY_PROFILE_ID),
        ),
        "metadata_profile": _resolve_profile_name(      # NEW
            config_data.get(CONF_LIDARR_METADATA_PROFILES, []),
            config_data.get(CONF_LIDARR_METADATA_PROFILE_ID),
        ),
        "root_folder": config_data.get(CONF_LIDARR_ROOT_FOLDER, ""),
    }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Music tab disabled placeholder | Activated Music tab | Phase 4 | Enables artist search and request |
| No `metadata_profile` in music results | Add to normalized result | Phase 4 | Dialog can show metadata profile name |
| Square poster for all results | Circular avatar for music | Phase 4 | Spotify/Apple Music convention; distinguishes music tab visually |

---

## Open Questions

1. **Lidarr `foreignArtistId` format**
   - What we know: Phase 2 normalizer already extracts `foreignArtistId` from Lidarr lookup results. It's present in the result.
   - What's unclear: Whether it's a UUID string or could be null for some artists.
   - Recommendation: Add null check in WS handler; if `foreign_artist_id` is None, return `error_code: "invalid_data"`. Treat as string throughout.

2. **Lidarr statistics in lookup response**
   - What we know: Similar to Sonarr, Lidarr's `/api/v1/artist/lookup` may not return `statistics` with track counts.
   - What's unclear: Whether any reliable "has downloaded tracks" signal exists in lookup results.
   - Recommendation: Do not attempt Available/Monitored distinction for music lookup results. All in-library artists → "Monitored" (blue), same pattern as Sonarr TV.

3. **`_normalize_music_result` already exists**
   - What we know: Phase 2 already implemented `_normalize_music_result` in websocket.py. It does NOT include `metadata_profile`.
   - What's unclear: Nothing — we just need to add `metadata_profile` to the returned dict.
   - Recommendation: Add `metadata_profile` field to the existing normalizer in Plan 04-01.

---

## Sources

### Primary (HIGH confidence)

- Existing `custom_components/requestarr/websocket.py` (Phase 2) — `_normalize_music_result` already extracts `foreignArtistId`, `quality_profile`, `root_folder`; pattern directly extended
- Existing `custom_components/requestarr/api.py` (Phase 1/2) — `ArrClient._request()` accepts `json=` kwarg; `async_request_movie`/`async_request_series` are direct templates
- Existing `custom_components/requestarr/const.py` — `CONF_LIDARR_METADATA_PROFILE_ID`, `CONF_LIDARR_METADATA_PROFILES`, `CONF_LIDARR_QUALITY_PROFILE_ID`, `CONF_LIDARR_ROOT_FOLDER` all present
- Existing `requestarr-card.js` (Phase 3) — Music tab placeholder already rendered as disabled button; `_doSearch`, `_doRequest`, `_renderDialog`, `_getItemState` all exist and need extension
- `.planning/phases/04-music-lidarr-request/04-CONTEXT.md` — All UI decisions locked (circular avatars, initials placeholder, parity with Phase 3)
- `.planning/STATE.md` — Lidarr uses `/api/v1/` (not `/api/v3/`); `metadataProfileId` fetched at config time and stored

### Secondary (MEDIUM confidence)

- Phase 3 research document — Radarr/Sonarr POST patterns verified; Lidarr follows same structural conventions with `foreignArtistId` substituting for `tmdbId`/`tvdbId`
- Lidarr community documentation — POST `/api/v1/artist` requires `foreignArtistId`, `qualityProfileId`, `metadataProfileId`, `rootFolderPath`, `monitored`, `addOptions`

### Tertiary (LOW confidence)

- None — all critical claims have primary source support from existing codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing Phase 1/2/3 code directly extended; no new frameworks
- Architecture: HIGH — Lidarr POST pattern mirrors Radarr/Sonarr; existing code is the template
- Pitfalls: HIGH — metadataProfileId requirement and foreignArtistId as string are directly derivable from the codebase inspection
- UI patterns: HIGH — circular avatar is CSS-only; CONTEXT.md specifies exact behavior

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (Lidarr API is stable; HA Lovelace patterns change slowly)
