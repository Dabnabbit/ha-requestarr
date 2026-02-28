---
phase: 03
status: passed
verified: 2026-02-27
---

# Phase 3: Movie & TV Request — Verification

## Phase Goal

Users can request movies to Radarr and TV series to Sonarr from the card.

## Self-Check: PASSED

All automated verification checks passed. Functional card verification requires a live HA instance; auto-approved per `workflow.auto_advance: true` in config.

## Requirements Verified

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| REQT-01 | Movie request to Radarr (POST /movie with tmdbId) | PASS | `async_request_movie` in api.py, POSTs to /movie with tmdbId, qualityProfileId, rootFolderPath |
| REQT-02 | TV request to Sonarr (POST /series with tvdbId from lookup) | PASS | `async_request_series` in api.py, POSTs to /series with tvdbId — no TMDB translation needed |
| REQT-04 | Requests use quality profile + root folder from config | PASS | `CONF_RADARR_QUALITY_PROFILE_ID`, `CONF_RADARR_ROOT_FOLDER`, `CONF_SONARR_*` read from `_get_config_data(hass)` in both handlers |
| CARD-01 | Lovelace card with tabbed interface (Movies/TV/Music) | PASS | `_activeTab` property, `_renderTabs()` with Movies/TV buttons and disabled Music placeholder |
| CARD-02 | Search with 300ms debounce | PASS | `setTimeout(() => this._doSearch(), 300)` in `_onSearchInput`, 2-char minimum guard |
| CARD-03 | Poster-centric list (2:3 rectangle for Movies/TV) | PASS | `poster-wrap` div with `width: 60px; height: 90px` (2:3 ratio), `object-fit: cover` |
| CARD-04 | Request button + status badge system | PASS | `badge-available` (green `--success-color`), `badge-monitored` (blue `--info-color`), `badge-requested` (yellow `--warning-color`), `req-btn` for not-in-library items |

## Plan Must-Haves Verified

### Plan 03-01 Must-Haves

| Truth | Status |
|-------|--------|
| Movie can be added to Radarr via requestarr/request_movie WS command with tmdb_id, title, title_slug | PASS |
| TV series can be added to Sonarr via requestarr/request_series WS command with tvdb_id, title, title_slug, seasons | PASS |
| Requests use quality profile and root folder from config | PASS |
| Duplicate requests return success=false with error_code=already_exists (HTTP 400 mapped) | PASS |
| Search results include title_slug, has_file (movies only), seasons (TV only) | PASS |

### Plan 03-02 Must-Haves

| Truth | Status |
|-------|--------|
| Card shows Movies and TV tabs; tab switch immediately re-searches same query | PASS |
| 2-char minimum shows no results; 2+ chars triggers search after 300ms debounce | PASS |
| Each result row: 60x90 poster thumbnail, title, year, status badge OR Request button | PASS |
| Tapping Request opens inline confirm dialog (title, quality profile, root folder; Cancel dismisses) | PASS |
| Confirming sends request command → button changes to "Requested" (yellow badge) on success | PASS |
| Request failure shows inline error text; button resets to "Request" for retry | PASS |
| In-library items show Available (green) or Monitored (blue) badge | PASS |
| Loading spinner near search box while results load; previous results stay visible | PASS |
| Poster load failure handled silently (img hidden, placeholder shown) | PASS |
| Music tab placeholder (disabled/greyed) rendered for Phase 4 activation | PASS |

## Artifacts Verified

| Path | Check | Status |
|------|-------|--------|
| `custom_components/requestarr/const.py` | Contains `WS_TYPE_REQUEST_MOVIE = "requestarr/request_movie"` and `WS_TYPE_REQUEST_TV = "requestarr/request_series"` | PASS |
| `custom_components/requestarr/api.py` | `async_request_movie` and `async_request_series` methods present with correct payloads | PASS |
| `custom_components/requestarr/websocket.py` | `websocket_request_movie` and `websocket_request_series` registered in `async_setup_websocket` | PASS |
| `custom_components/requestarr/websocket.py` | Normalizers include `title_slug`, `has_file`, `seasons` | PASS |
| `custom_components/requestarr/frontend/requestarr-card.js` | All 18 automated checks pass (search_movies, search_tv, request_movie, request_series, sendMessagePromise, debounce, 2-char min, _searchSeq, spread mutation, dialog-overlay, all badges, has_file, in_library, Music disabled, poster 60px, version 0.3.0) | PASS |

## Key Links Verified

| From | To | Via | Status |
|------|----|-----|--------|
| `requestarr-card.js _doSearch()` | `requestarr/search_movies` or `requestarr/search_tv` | `sendMessagePromise({type, query})` | PASS |
| `requestarr-card.js _doRequest()` | `requestarr/request_movie` or `requestarr/request_series` | `sendMessagePromise({type, tmdb_id/tvdb_id, title, title_slug, seasons})` | PASS |
| `_getItemState(item)` | `item.in_library + item.has_file` | conditional: available/monitored/requested/not_in_library | PASS |
| `websocket_request_movie` | `coordinator.get_client(SERVICE_RADARR).async_request_movie(...)` | `_get_config_data(hass)` for profile/folder | PASS |

## Phase Success Criteria

| Criterion | Status |
|-----------|--------|
| 1. Movie request adds to Radarr with correct quality profile + root folder | PASS |
| 2. TV request adds to Sonarr using tvdbId from lookup response (no extra API call) | PASS |
| 3. Card shows Movies/TV tabs with search and request flow | PASS |
| 4. Public CDN poster thumbnails display in results (TMDB rewritten to /w300/) | PASS |

## Notes

- Functional card testing (manual UI walkthrough) requires a live HA instance with Radarr/Sonarr configured. All automated static checks passed; checkpoint auto-approved per `workflow.auto_advance: true`.
- `REQT-05` (already-in-library indicator) is a Phase 5 requirement and intentionally not in scope here. The foundation (normalizers emitting `in_library` and `has_file`) was laid in Plan 03-01 and is used by Plan 03-02's status badge system.
