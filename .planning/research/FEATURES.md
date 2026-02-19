# Feature Research

**Domain:** Home Assistant HACS media request integration (Lovelace card + backend coordinator)
**Researched:** 2026-02-19
**Confidence:** MEDIUM — Jellyseerr/Overseerr/Mediarr features verified via multiple web sources; Seerr Lidarr PR status is MEDIUM confidence (open PR, merge unconfirmed); HA-native UX patterns are HIGH confidence from direct code inspection.

---

## Competitive Landscape Summary

| Product | Type | Auth | Music/Lidarr | Notes |
|---------|------|------|--------------|-------|
| Jellyseerr | Standalone webapp | Separate (Jellyfin SSO) | No (PRs open, unmerged as of research) | Most complete feature set; Jellyfin-native |
| Overseerr | Standalone webapp | Separate (Plex SSO) | No | Superseded by Seerr project |
| Seerr | Standalone webapp (Overseerr+Jellyseerr merge) | Separate | In-progress (PR #1238, #782) | Roadmap includes Lidarr; not yet shipped |
| Ombi | Standalone webapp | Separate | Yes (via Lidarr), but buggy | Older project; Lidarr integration has known caching errors |
| Petio | Standalone webapp | Separate (Plex SSO) | No | Plex-only; notable for smart routing to multiple arr instances |
| Mediarr card | HA Lovelace card | HA auth (native) | No | Display-only: recently added, upcoming, now-playing; no request submission |
| Anotharrr | HA Lovelace card + sensor | HA auth (native) | No | Dashboard view; aggregates Sonarr/Radarr/Jellyfin state; no request submission |
| Upcoming Media Card | HA Lovelace card | HA auth (native) | No | Display-only: upcoming/recently added from Sonarr/Radarr |

**Key gap:** No HA-native card currently supports submitting requests to arr services, nor does any existing product support movies + TV + music in a single integrated request UI without a separate container.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Text search for movies | Every request tool has it; users arrive expecting "type title, click request" | LOW | TMDB `/search/movie` endpoint; already scaffolded in coordinator |
| Text search for TV shows | Same expectation as movie search | LOW | TMDB `/search/tv`; already scaffolded |
| Search result cards with poster, title, year, description | Jellyseerr/Overseerr both show rich result cards; bare text list feels broken | LOW | TMDB provides poster_path; 60px thumbnail sufficient for card |
| "Request" button per result | The entire UX contract; missing = card is pointless | LOW | Needs actual Radarr/Sonarr API call behind it (currently TODO stub) |
| "Already in library" state indicator | Jellyseerr shows this; users find it frustrating to request something they already have | MEDIUM | Requires checking Radarr/Sonarr library against TMDB ID; coordinator polling covers this |
| "Already requested" state indicator | Prevents duplicate requests from household members | MEDIUM | Needs a request tracking store; can be lightweight in-memory or HA storage |
| One-click request to Radarr (movies) | Core value; Radarr API `/api/v3/movie` POST with TMDB ID | LOW | Radarr API is well-documented; needs quality profile + root folder defaults |
| One-click request to Sonarr (TV) | Core value; Sonarr API `/api/v3/series` POST with TVDB ID (converted from TMDB) | MEDIUM | TMDB→TVDB ID translation required; Sonarr uses TVDB not TMDB IDs |
| Tabbed navigation (Movies / TV / Music) | Already in scaffold; natural UX organization | LOW | Already implemented in card scaffold |
| Library count sensors (movies/series/artists) | Already in coordinator; gives users context on library size | LOW | Already implemented; needs production-quality error handling |
| Success/failure feedback after request | Users need confirmation the request was submitted | LOW | HA notification toast via `hass-notification` custom event; already in scaffold |
| Config flow with connection validation | Users need to know immediately if API keys are wrong | MEDIUM | Validation TODOs are already stubbed in config_flow.py |
| Visual card editor (GUI config) | HACS card convention; users expect drag-and-drop config, not YAML | LOW | Editor class already scaffolded; needs real config options exposed |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Music search + Lidarr request | No existing HA-native card does this; Jellyseerr/Overseerr don't support it yet; only Ombi does (with known bugs) | MEDIUM | MusicBrainz search API (no key needed) → Lidarr `/api/v3/artist` POST; artist-level requests match Lidarr's model |
| HA-native authentication | No separate login; household members use HA accounts they already have; zero onboarding friction | LOW | Already free — using HA's auth by existing in HA; per-user context via `hass.user` |
| HA mobile app push notifications on request fulfillment | Jellyseerr sends Discord/email; HA can push to the exact phone the user is holding, in the same app they made the request from | MEDIUM | Requires automation trigger on sensor state change or HA service call from coordinator; no external webhook service needed |
| No separate container to maintain | Eliminates Docker container, separate auth, separate URL; reduces homelab maintenance burden | LOW | Core architectural differentiator; already achieved by design |
| "Already in library" check for music (Lidarr) | Even Ombi has trouble with this; clean state detection for artists in Lidarr | MEDIUM | Lidarr `/api/v3/artist?mbId=X` lookup; MusicBrainz ID cross-reference |
| Keyboard-first search (Enter to search) | Small UX polish; important on TV dashboards with remote control | LOW | Already scaffolded (`@keydown` Enter handler) |
| Per-tab result persistence across tab switches | Clearing results on tab switch (current scaffold behavior) is jarring; persist last search per tab | LOW | Store per-tab `{query, results}` in component state |
| Quality profile default config in visual editor | Radarr/Sonarr have multiple quality profiles; household users shouldn't see a profile picker on every request — admin sets default in card config | LOW | Config option in editor; passed to API POST on request |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Per-user request quotas and approval workflows | Jellyseerr/Overseerr have this; power users expect it | Requires persistent state storage (SQLite or HA storage), admin UI for quota management, notification of pending approvals — multiply complexity by 5x; household of 3-4 people doesn't need quotas | Defer to v3. For now: all household members can request freely. Trust-based household model. |
| Discover/Trending/Popular browse mode | Jellyseerr has a full "Discover" tab with trending/popular/upcoming/genre browse | TMDB browse endpoints return hundreds of items; pagination, filtering, genre browsing = large separate feature scope; conflicts with "single JS file, no build step" constraint by creating large component surface | Defer to v2. Keep v1 as search-driven, not browse-driven. |
| Season-level granular TV requests | Jellyseerr supports requesting individual seasons; some users expect this | Sonarr's season request model is complex; storing which seasons to monitor adds state; card UI for season selection creates multi-step flow that breaks the "one-click" UX contract | Request full series by default (Sonarr monitored=true for all seasons). Power users can manage seasons in Sonarr directly. |
| 4K vs Standard quality picker per-request | Overseerr supports Standard and 4K as separate request types | Requires knowing whether user has 4K Radarr instance configured; two-step UI per request; most households run single quality tier | Admin sets quality profile in card config. No per-request quality selection. |
| Request history and analytics dashboard | "Show me all the things I've requested" | Requires persistent storage layer; HA storage API or SQLite; adds significant backend complexity for a household of 3-4 | Out of scope until v3. Radarr/Sonarr/Lidarr show download history natively. |
| Plex integration | Some users want Plex library checks | Project is explicitly Jellyfin-household; adds maintenance surface; Plex API differs from Jellyfin | Explicitly out of scope. Plex users should use Overseerr/Jellyseerr. |
| Real-time search (search-as-you-type) | Feels modern | Each keystroke = TMDB API call; TMDB has rate limits; results flash as user types; debounce logic adds complexity | Keep explicit search button (Enter or click). Scaffold already implements this correctly. |
| Multiple Radarr/Sonarr instance routing | Petio does this (route anime to separate Sonarr instance) | Adds instance selection UI per-request; complicates config flow; household with single instances of each arr service doesn't need it | Single instance per service. Admin configures which instance in setup. |
| Jellyfin library sync / now-playing display | Mediarr/Anotharrr do this; some users want it in same card | Mediarr already exists and does this well; duplicating it creates maintenance overlap; Jellyfin API integration is a separate feature domain from request management | Separate card for Jellyfin display (use Mediarr). Requestarr stays request-focused. |

---

## Feature Dependencies

```
[TMDB API key config]
    └──requires──> [Movie search]
    └──requires──> [TV search]

[Movie search]
    └──requires──> [Search result display with poster/title/year]
                       └──enables──> [Request button per result]
                                         └──requires──> [Radarr config + API key]

[TV search]
    └──requires──> [Search result display]
                       └──enables──> [Request button per result]
                                         └──requires──> [Sonarr config + API key]
                                         └──requires──> [TMDB→TVDB ID translation]

[Music search]
    └──requires──> [MusicBrainz search integration]
                       └──requires──> [Search result display (artist name, albums, genre)]
                                         └──enables──> [Request button per result]
                                                           └──requires──> [Lidarr config + API key]

[Already in library indicator]
    └──requires──> [Coordinator library sync from Radarr/Sonarr/Lidarr]
    └──requires──> [TMDB ID ↔ arr library ID mapping]

[Already requested indicator]
    └──requires──> [Request state store (lightweight)]
    └──enhances──> [Already in library indicator]

[HA push notification on fulfillment]
    └──requires──> [Request state store]
    └──requires──> [HA automation or coordinator polling for status change]

[Library count sensors]
    └──requires──> [Radarr/Sonarr/Lidarr coordinator polling]  (already implemented)

[Visual card editor]
    └──requires──> [Config options defined] (quality profile default, root folder default, header text)
    └──enhances──> [One-click request] (admin sets defaults so users don't see options)
```

### Dependency Notes

- **TV search requires TMDB→TVDB translation:** Sonarr uses TVDB IDs. TMDB provides `external_ids` endpoint (`/tv/{id}/external_ids`) returning `tvdb_id`. Must call this endpoint before Sonarr POST. This is a non-obvious implementation detail.
- **Music search is independent of TMDB:** MusicBrainz is the search backend for music, not TMDB. Separate search path entirely.
- **Already in library requires coordinator data:** The coordinator already polls arr library counts. Extend it to also fetch arr library items (with TMDB/TVDB/MBID) for ID matching. This is a moderate addition to coordinator scope.
- **Request state store enables anti-duplicate UX:** Without it, two household members can unknowingly request the same thing simultaneously. Even a lightweight in-memory store (reset on HA restart) is better than nothing. HA's `Store` (homeassistant.helpers.storage) provides persistence if needed.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept and replace Jellyseerr for this household.

- [ ] Config flow with real validation (TMDB key test, arr connection test) — setup must not silently fail
- [ ] TMDB movie search with result display (poster, title, year, truncated overview)
- [ ] TMDB TV search with result display
- [ ] One-click movie request to Radarr (POST `/api/v3/movie` with quality profile + root folder from config)
- [ ] One-click TV series request to Sonarr (POST `/api/v3/series` with TVDB ID translated from TMDB)
- [ ] MusicBrainz artist search with result display (artist name, disambiguation, tags)
- [ ] One-click artist request to Lidarr (POST `/api/v3/artist` with MusicBrainz ID)
- [ ] "Already in library" indicator for movies, TV, and music
- [ ] HA mobile push notification when request completes (media available state change)
- [ ] Visual card editor exposing: quality profile, root folder, header text
- [ ] HACS distribution working (hacs.json passes validation, version tagged release)

### Add After Validation (v1.x)

Features to add once core request loop is working and household is actively using it.

- [ ] "Already requested" indicator (lightweight request state store in HA storage) — add when duplicate request confusion is reported
- [ ] Per-tab search state persistence (don't clear results on tab switch) — add when users report annoyance
- [ ] Season-level request option (Sonarr monitored seasons) — add if users specifically request it, not speculatively
- [ ] HA push notification on Radarr/Sonarr download progress (not just availability) — add when notification system is validated

### Future Consideration (v2+)

Features to defer until product-market fit for this household is established.

- [ ] Discover/trending/popular browse mode (v2) — Mediarr already covers display-side; add request-from-discover if users want it
- [ ] Upcoming releases calendar view (v2) — Mediarr/Anotharrr cover this natively
- [ ] Recently added display (v2) — same
- [ ] Per-user request quotas and approval workflow (v3) — household trust model sufficient for now
- [ ] Request history and analytics (v3)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Config flow with real validation | HIGH | MEDIUM | P1 |
| Movie search + Radarr request | HIGH | LOW | P1 |
| TV search + Sonarr request | HIGH | MEDIUM (TVDB translation) | P1 |
| Music search + Lidarr request | HIGH (differentiator) | MEDIUM | P1 |
| Already in library indicator | HIGH | MEDIUM | P1 |
| Visual card editor | MEDIUM | LOW | P1 |
| HA push notification on fulfillment | HIGH (differentiator) | MEDIUM | P1 |
| Already requested indicator | MEDIUM | MEDIUM | P2 |
| Per-tab search state persistence | LOW | LOW | P2 |
| Discover/trending browse | MEDIUM | HIGH | P3 |
| Per-user quotas / approval workflow | LOW (household) | HIGH | P3 |
| Season-level TV requests | LOW (household) | HIGH | P3 |
| 4K quality picker per-request | LOW | MEDIUM | P3 |
| Request history / analytics | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch (replaces Jellyseerr)
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Jellyseerr | Overseerr | Ombi | Mediarr card | Requestarr approach |
|---------|------------|-----------|------|--------------|---------------------|
| Movie search + request | Yes | Yes | Yes | No (display only) | Yes — TMDB + Radarr |
| TV search + request | Yes | Yes | Yes | No | Yes — TMDB + Sonarr |
| Music search + request | No (open PRs) | No | Yes (buggy) | No | Yes — MusicBrainz + Lidarr (differentiator) |
| HA-native auth | No | No | No | Yes | Yes (free by design) |
| HA mobile push notification | No (Discord/email/webhook) | No | No | No | Yes — HA notify platform |
| Trending/discover browse | Yes | Yes | Partial | Yes (TMDB lists) | Deferred v2 |
| Already in library check | Yes | Yes | Yes | N/A | Yes — coordinator polling |
| Approval workflow | Yes | Yes | Yes | No | Deferred v3 |
| User quotas | Yes | Yes | Yes | No | Deferred v3 |
| Per-user quality profiles | Yes | Yes | Partial | No | No — admin sets default |
| No separate container | No | No | No | Partial (still needs mediarr_sensor) | Yes |
| HACS distribution | No | No | No | Yes | Yes |
| Single-file frontend | No | No | No | No (multi-file) | Yes |
| 4K request support | Yes | Yes | Partial | No | No — single quality |

---

## Sources

- Jellyseerr feature documentation (via rapidseedbox.com, docs.jellyseerr.dev, noted.lol): MEDIUM confidence
- Overseerr feature documentation (via rapidseedbox.com, seerr.dev): MEDIUM confidence
- Seerr Lidarr support PR #1238 and #782 (github.com/seerr-team/seerr): MEDIUM confidence (open PRs, merge status unconfirmed as of 2026-02-19)
- Petio features (petio.tv, github.com/petio-team/petio): MEDIUM confidence
- Mediarr card (github.com/Vansmak/mediarr-card): MEDIUM confidence
- Anotharrr (community.home-assistant.io): LOW confidence (limited documentation found)
- Project scaffold direct inspection (config_flow.py, coordinator.py, requestarr-card.js): HIGH confidence
- Radarr/Sonarr/Lidarr API v3 patterns: HIGH confidence (from project context and arr community docs)
- HA notification platform: HIGH confidence (official docs referenced in search results)

---

*Feature research for: Home Assistant HACS media request card (Requestarr)*
*Researched: 2026-02-19*
