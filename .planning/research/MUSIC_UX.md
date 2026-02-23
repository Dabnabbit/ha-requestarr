# Music Tab UX Research: Artist Search & Request Flow

**Research Date:** 2026-02-23
**Context:** Jellyseerr does not support music. The Music tab in Requestarr needs its own UX design informed by Lidarr's UI, Ombi's music flow, MusicBrainz data availability, and music app patterns from Spotify/Apple Music/YouTube Music.
**Companion to:** JELLYSEERR_UX.md (movie/TV UX analysis)

---

## Table of Contents

1. [Lidarr's Add Artist UI](#1-lidarrs-add-artist-ui)
2. [Ombi's Music Request Flow](#2-ombis-music-request-flow)
3. [MusicBrainz Data Availability](#3-musicbrainz-data-availability)
4. [Album Art as Visual Proxy (Cover Art Archive)](#4-album-art-as-visual-proxy-cover-art-archive)
5. [Fanart.tv Artist Images](#5-fanarttv-artist-images)
6. [Music App UX Patterns](#6-music-app-ux-patterns)
7. [Lidarr API Response Shape](#7-lidarr-api-response-shape)
8. [Recommended Music Tab UX Design](#8-recommended-music-tab-ux-design)
9. [Implementation Decision Summary](#9-implementation-decision-summary)

---

## 1. Lidarr's Add Artist UI

### Search Results Display

**Source:** `frontend/src/Search/Artist/AddNewArtistSearchResult.js` (Lidarr GitHub repo, `develop` branch)

Lidarr presents artist search results as **full-width horizontal cards** (not a poster grid like Jellyseerr). Each search result row displays:

| Element | Details |
|---------|---------|
| **Artist poster** | 170px wide x 250px tall, left-aligned. Hidden on small screens. Uses `ArtistPoster` component with `images` array from API. |
| **Artist name** | Large text (36px, font-weight: 300). |
| **Year** | Shown in parentheses after name, muted color. Only if not already in the artist name. |
| **Disambiguation** | Shown in parentheses after year, muted color. E.g., "(90s US grunge band)". |
| **Rating** | Heart-based rating via `HeartRating` component, displayed in a `Label` pill. |
| **Artist type** | "Group" or "Person", displayed in a `Label` pill. |
| **Status** | "Inactive" or "Deceased" badge (red/danger kind) shown only when `status === 'ended'`. Uses localized strings: `artistType === 'Person'` shows "Deceased", otherwise "Inactive". |
| **Overview** | Truncated biography text below the metadata row. Dynamic height calculation based on row height (230px base minus padding). |
| **"Already in library" icon** | Green checkmark circle icon (36px, color `#37bc9b`) if `isExistingArtist` is true. |
| **MusicBrainz link** | External link icon (28px) linking to `musicbrainz.org/artist/{foreignArtistId}`. |

**CSS layout:** Flexbox row with `.poster` at `flex: 0 0 170px` and `.content` at `flex: 0 1 100%`. Result row has 20px padding and margin. Hover state adds box-shadow and background transition. Name row uses nested flex for alignment.

**Interaction:** Clicking a result that is NOT in the library opens the `AddNewArtistModal`. Clicking one that IS in the library navigates to the existing artist detail page via `to: /artist/${foreignArtistId}`.

### Add Artist Modal

**Source:** `frontend/src/Search/Artist/AddNewArtistModalContent.js`

The modal contains:
- Artist poster (250px, hidden on small screens)
- Artist name (bold)
- Disambiguation text in parentheses
- Overview (truncated to 8 lines via `TextTruncate`)
- **AddArtistOptionsForm** with these fields:
  - Root Folder (dropdown with path selector)
  - Monitor (dropdown: None/All/Future/Missing/Latest/First)
  - Monitor New Items (dropdown)
  - Quality Profile (dropdown)
  - Metadata Profile (dropdown, conditionally hidden)
  - Tags (multi-select)
- "Search for missing albums" checkbox in footer
- "Add {Artist Name}" button (green/success spinner button)

**Source:** `frontend/src/Search/Common/AddArtistOptionsForm.js`

**Click count:** Search (type query) -> Click result -> Configure options -> Click "Add" = **3-4 interactions**. The configuration options (6 form fields) add friction that a household request card should eliminate by using preconfigured defaults.

### Key Takeaway for Requestarr

Lidarr's search result card shows: **poster, name, year, disambiguation, type (Group/Person), rating, status, overview, and "in library" indicator**. This is more information-dense than Jellyseerr's movie cards. For the Requestarr music tab, the minimum useful display is: **name, disambiguation, type, top genre tag, and "in library" indicator**. The poster is problematic because artist images are sourced from fanart.tv and many artists lack coverage (see Section 5).

---

## 2. Ombi's Music Request Flow

### Search Flow Architecture

**Source:** Ombi GitHub repo (`develop` branch), multiple frontend components

Ombi V2 uses the same `discover-card` component for all media types (movies, TV, music). The search results page (`search-results.component.html`) renders a responsive grid of `discover-card` components with infinite scroll. Each card shows:

| Element | Details |
|---------|---------|
| **Type label** | Top-left corner: "Movie", "Tv", or "Artist" (from `RequestType` enum) |
| **Status indicator** | Top-right: colored dot + text ("Available", "Processing", etc.) |
| **Poster image** | Main card image from `result.posterPath`. For music, this is problematic. |
| **Title** | Overlaid on poster on hover (class `middle`) |
| **Overview** | Brief description overlaid on poster on hover, truncated with ellipsis |
| **Request button** | Cloud download icon + "Request" text, shown if not already available/requested/approved |

### Artist Detail Page

**Source:** `media-details/components/artist/artist-details.component.html`

When clicking an artist card, Ombi navigates to a full detail page showing:

- **Top banner** with artist name as title and disambiguation as tagline
- **Poster image** (left column via `<media-poster>` component)
- **Social/external links** (homepage, IMDB, Twitter, Facebook, Instagram, Spotify, Deezer, Google, Apple, and more via `<social-icons>` component)
- **"Request All Albums" button** (primary, always visible)
- **"Request Selected Albums" button** (appears when albums are manually selected)
- **"Clear Selection" button** (accent color, appears when albums selected)
- **Artist information panel** (left sidebar card) displaying:
  - Type (e.g., "Group", "Person")
  - Country
  - Start Date (year)
  - End Date (if applicable)
- **Overview** text (biography) in a card
- **Release groups panel** (`<artist-release-panel>`) with selectable albums, each emitting selection events
- **Issues panel** (if request exists)

### Data Sources

**Source:** `Ombi.Core/Engine/V2/MusicSearchEngineV2.cs`

Ombi's music search engine combines data from two sources:

1. **MusicBrainz API** via `_musicBrainzApi`:
   - Artist name, type, country, region (`area.name`), disambiguation
   - Life span (start year, end year)
   - Release groups (albums) with primary type, title, first release date
   - Band members (name, attributes, current membership, start/end dates)
   - External links (extracted from MusicBrainz relations)

2. **Lidarr API** via `_lidarrApi.GetArtistByForeignId()` (if configured):
   - Artist images:
     - `banner` = image where `coverType === "banner"`
     - `logo` = image where `coverType === "logo"`
     - `poster` = image where `coverType === "poster"`
     - `fanart` = image where `coverType === "fanart"`
   - `overview` (biography text)
   - All image URLs converted to HTTPS via `.ToHttpsUrl()`

**Critical finding:** Ombi gets artist images FROM Lidarr, not from MusicBrainz. Lidarr sources its images from fanart.tv and other metadata providers. If Lidarr does not already have the artist indexed, the `GetArtistByForeignId` call may fail (caught as `JsonSerializationException` and swallowed), resulting in no images.

### Ombi Music Search Data Models

**Source:** `ClientApp/src/app/interfaces/ISearchMusicResult.ts` (V1)

```typescript
interface ISearchArtistResult {
  artistName: string;
  artistType: string;
  disambiguation: string;
  forignArtistId: string;  // note: typo in original
  banner: string;
  overview: string;
  poster: string;
  monitored: boolean;
  approved: boolean;
  requested: boolean;
  requestId: number;
  available: boolean;
  links: ILink[];
  subscribed: boolean;
  showSubscribe: boolean;
  requestProcessing: boolean;
  processed: boolean;
  background: any;
}
```

**Source:** `ClientApp/src/app/interfaces/IMusicSearchResultV2.ts` (V2, richer)

```typescript
interface IArtistSearchResult {
  name: string;
  id: string;
  startYear: string;
  endYear: string;
  type: string;
  country: string;
  region: string;
  disambiguation: string;
  banner: string;
  logo: string;
  poster: string;
  fanArt: string;
  releaseGroups: IReleaseGroups[];
  links: IArtistLinks;       // 18+ external link fields
  members: IBandMembers[];
  overview: string;
  background: any;
}
```

### Known Issues

Ombi's music integration has significant documented problems:

| Issue | Description | Impact |
|-------|-------------|--------|
| [#4941](https://github.com/Ombi-app/Ombi/issues/4941) | Search results mislabel artist types as "Album" instead of "Group"/"Person" | Confusing UI |
| [#4271](https://github.com/Ombi-app/Ombi/issues/4271) | Artist names and album artwork missing from results; attributed to switch from Last.fm to MusicBrainz | Broken display |
| [#3027](https://github.com/Ombi-app/Ombi/issues/3027) | "View albums" functionality times out or never loads | Feature broken |
| [#2805](https://github.com/Ombi-app/Ombi/issues/2805) | Requested albums go to blackhole if Lidarr does not recognize them | Silent failures |
| [#4608](https://github.com/Ombi-app/Ombi/issues/4608) | Artists not set to monitored in Lidarr after request | Requests never fulfilled |
| [#2549](https://github.com/Ombi-app/Ombi/issues/2549) | Lidarr search not triggered when artist added from Ombi | Downloads never start |
| [#4809](https://github.com/Ombi-app/Ombi/issues/4809) | "Music Searches are Terrible" (user title) | General poor quality |

### Click Count Analysis

**Artist request flow (Ombi):**
1. Type search query (search-as-you-type)
2. Click artist card in results grid
3. Navigate to artist detail page (full page load)
4. Click "Request All Albums" or select specific albums
5. Confirm (if applicable)

**Total: 4-5 interactions** for "request all", more for selective album requests.

### Key Takeaway for Requestarr

Ombi's music UX is widely reported as broken/buggy. The key lessons:
1. Do NOT rely on album-level selection for the initial v1 flow. Artist-level requests (matching Lidarr's "add artist, monitor all" model) are the simpler, more reliable path.
2. The image problem is real -- Ombi works around it by pulling from Lidarr's image cache, which only works for artists Lidarr already knows about. For new-to-Lidarr artists, expect no images.
3. Plan for robust placeholder/fallback design as a first-class concern, not an afterthought.
4. Album requests that Lidarr cannot fulfill create silent failures. Stick to artist-level requests for v1.

---

## 3. MusicBrainz Data Availability

### Artist Search Endpoint

**URL:** `https://musicbrainz.org/ws/2/artist/?query={term}&fmt=json&limit={n}&offset={n}`

**Rate limiting:** MusicBrainz requires a descriptive `User-Agent` header (format: `AppName/Version (contact-email)`). Rate limit is **1 request per second** for unauthenticated access. The server returns **503** if the rate limit is exceeded.

**No API key required.** Free and open access.

### Complete Response Shape (verified via live API call)

Querying for "radiohead" with `limit=2` returned:

```json
{
  "created": "2026-02-23T19:57:56.578Z",
  "count": 27,
  "offset": 0,
  "artists": [
    {
      "id": "a74b1b7f-71a5-4011-9441-d0b5e4122711",
      "type": "Group",
      "type-id": "e431f5f6-b5d2-343d-8b36-72607fffb74b",
      "score": 100,
      "name": "Radiohead",
      "sort-name": "Radiohead",
      "country": "GB",
      "area": {
        "id": "8a754a16-0027-3a29-b6d7-2b40ea0481ed",
        "type": "Country",
        "type-id": "06dd0ae4-8c74-30bb-b43d-95dcedf961de",
        "name": "United Kingdom",
        "sort-name": "United Kingdom",
        "life-span": { "ended": null }
      },
      "begin-area": {
        "id": "d840d4b3-8987-4626-928b-398de760cc24",
        "type": "City",
        "type-id": "6fd8f29a-3d0a-32fc-980d-ea697b69da78",
        "name": "Abingdon-on-Thames",
        "sort-name": "Abingdon-on-Thames",
        "life-span": { "ended": null }
      },
      "isnis": ["0000000115475162"],
      "life-span": {
        "begin": "1991",
        "ended": null
      },
      "aliases": [
        { "name": "Radio Head", "sort-name": "Radio Head", "type": "Search hint", "locale": null, "primary": null },
        { "name": "\u30ec\u30c7\u30a3\u30aa\u30d8\u30c3\u30c9", "sort-name": "...", "type": "Artist name", "locale": "ja", "primary": true }
      ],
      "tags": [
        { "count": 42, "name": "alternative rock" },
        { "count": 29, "name": "art rock" },
        { "count": 17, "name": "rock" },
        { "count": 14, "name": "experimental rock" },
        { "count": 14, "name": "british" },
        { "count": 13, "name": "electronic" },
        { "count": 4, "name": "indie rock" },
        { "count": 3, "name": "art pop" },
        { "count": 2, "name": "experimental" },
        { "count": 2, "name": "electronica" },
        { "count": 2, "name": "alternative" }
      ],
      "disambiguation": ""
    },
    {
      "id": "c74f4726-2671-4011-81b6-f70da905c05a",
      "type": "Group",
      "type-id": "e431f5f6-b5d2-343d-8b36-72607fffb74b",
      "score": 64,
      "name": "On a Friday",
      "sort-name": "On a Friday",
      "disambiguation": "pre\u2010Radiohead group, until 1991",
      "area": { "type": "City", "name": "Abingdon-on-Thames" },
      "begin-area": { "type": "City", "name": "Abingdon-on-Thames" },
      "life-span": { "begin": "1985", "end": "1991", "ended": true },
      "aliases": [
        { "name": "Radiohead", "type": "Search hint" },
        { "name": "Shindig", "type": null }
      ],
      "tags": [
        { "count": 1, "name": "indie pop" },
        { "count": 1, "name": "uk" },
        { "count": 1, "name": "oxford" },
        { "count": 1, "name": "united kingdom" }
      ]
    }
  ]
}
```

### Field Availability Matrix

| Field | Available? | Useful for Card? | Notes |
|-------|-----------|-----------------|-------|
| `id` (MBID) | Always | Yes (primary key, Lidarr foreign ID) | UUID format |
| `name` | Always | Yes (primary display) | |
| `type` | Usually | Yes ("Group", "Person", "Orchestra", "Choir", "Character", "Other") | Occasionally null |
| `score` | Always | No (internal ranking) | 0-100, useful for result ordering |
| `country` | Often | Maybe (secondary info) | ISO 3166-1 alpha-2 code ("GB", "US", "DE") |
| `area.name` | Often | Maybe | Full country/region name ("United Kingdom") |
| `begin-area.name` | Sometimes | No | Origin city -- too detailed for compact card |
| `disambiguation` | Sometimes | Yes (critical for distinguishing same-name artists) | E.g., "90s US grunge band", "pre-Radiohead group, until 1991" |
| `life-span.begin` | Often | Yes (active-since year) | Year string, e.g., "1991" |
| `life-span.end` | When ended | Yes (if ended) | |
| `life-span.ended` | Always | Yes (active vs. inactive indicator) | Boolean or null |
| `aliases` | Often | No (for search engine, not display) | Array of alternative names |
| `tags` | Often | Yes (top 1-2 as genre proxy) | Array with vote counts; filter by `count > 0` and sort desc |
| `sort-name` | Always | No | |
| **`images`** | **NEVER** | **N/A** | **MusicBrainz search does NOT return images** |
| **`release-groups`** | **NOT in search** | **N/A** | Must use lookup endpoint with `inc=release-groups` |
| **`overview`** | **NOT available** | **N/A** | MusicBrainz has no biography/overview text |

### Critical Finding: No Images from MusicBrainz

**MusicBrainz does not store or serve artist images.** The search endpoint returns zero image data. This is a fundamental difference from TMDB (which provides `poster_path` for movies/TV). Any visual element for music artist cards must come from external sources.

### Tags as Genre Proxy

MusicBrainz tags are user-voted and can be noisy. The Radiohead example returned 42+ tags. To extract useful genre information:
1. Filter tags where `count > 0`
2. Sort by `count` descending
3. Take top 2-3 tags
4. Result: "alternative rock" (42), "art rock" (29), "rock" (17) for Radiohead

Some tags are geographic ("british", "uk"), temporal ("1992-1998"), or junk ("lolicore", "sacred cows"). Filtering by `count >= 2` eliminates most noise.

### Key Takeaway for Requestarr

MusicBrainz provides rich textual metadata (name, type, disambiguation, country, active years, tags) but **zero visual content and no biography text**. The card must be designed text-first with visual fallbacks. Tags with highest vote counts serve as reliable genre indicators but need filtering.

---

## 4. Album Art as Visual Proxy (Cover Art Archive)

### API Overview

The Cover Art Archive (CAA) is a joint project between the Internet Archive and MusicBrainz. It stores album artwork submitted and curated by the MusicBrainz community.

**Base URL:** `https://coverartarchive.org`

### Relevant Endpoints

| Endpoint | Returns | HTTP Method |
|----------|---------|-------------|
| `/release-group/{mbid}/` | JSON listing of all cover art for a release group | GET (200) |
| `/release-group/{mbid}/front` | 307 redirect to front cover image | GET (307) |
| `/release-group/{mbid}/front-250` | 307 redirect to 250px thumbnail | GET (307) |
| `/release-group/{mbid}/front-500` | 307 redirect to 500px thumbnail | GET (307) |
| `/release-group/{mbid}/front-1200` | 307 redirect to 1200px image | GET (307) |
| `/release/{mbid}/` | JSON listing for a specific release | GET (200) |
| `/release/{mbid}/front[-size]` | Same as above but for specific release | GET (307) |

### Thumbnail Sizes

- **250px** - Suitable for card thumbnails and list rows
- **500px** - Medium resolution for detail views
- **1200px** - Full resolution

Legacy aliases: `"small"` = 250, `"large"` = 500

### JSON Response Structure

```json
{
  "images": [
    {
      "image": "https://archive.org/...",
      "thumbnails": {
        "250": "https://archive.org/...-250.jpg",
        "500": "https://archive.org/...-500.jpg",
        "1200": "https://archive.org/...-1200.jpg",
        "small": "https://archive.org/...-250.jpg",
        "large": "https://archive.org/...-500.jpg"
      },
      "types": ["Front"],
      "front": true,
      "back": false,
      "comment": "",
      "approved": true,
      "edit": 12345,
      "id": 67890
    }
  ],
  "release": "https://musicbrainz.org/release/..."
}
```

### HTTP Response Codes

- **200** - JSON listing returned
- **307** - Redirect to image at archive.org
- **400** - Invalid MBID format
- **404** - No artwork found or release group does not exist
- **503** - Rate limit exceeded

### Strategy for Using CAA as Artist Thumbnails

Since CAA provides per-album art (not per-artist), the flow to get a "thumbnail" for an artist would be:

1. Search MusicBrainz for artist (get MBID)
2. Look up artist by MBID with `?inc=release-groups` to get their albums
3. Pick the most popular/first release group MBID
4. Request `coverartarchive.org/release-group/{rg-mbid}/front-250`
5. Follow 307 redirect to actual image

**Problems with this approach:**
- Requires **3 sequential API calls** (search -> lookup with release-groups -> CAA)
- MusicBrainz rate limit (1 req/sec) makes this slow for 8 results = 8+ seconds
- Not all release groups have cover art (404 response)
- Album art is **not recognizable as the artist** the way a portrait photo would be
- A random album cover next to an artist name creates confusing visual association
- Adds significant latency to search results rendering

### Key Takeaway for Requestarr

Using Cover Art Archive for artist thumbnails is technically possible but **not practical for search results**. The 3-hop chain (search -> lookup release groups -> CAA redirect) adds too much latency and the result (album cover as artist proxy) is semantically confusing. Better use cases for CAA:
- Album thumbnails in an album selection view (v2 feature)
- Detail view enrichment after user clicks into an artist
- NOT for search result list items

---

## 5. Fanart.tv Artist Images

### API Overview

Fanart.tv provides high-quality, community-curated images for movies, TV shows, and music artists. It is the primary source Lidarr uses for artist images.

**Endpoint:** `GET https://webservice.fanart.tv/v3.2/music/{musicbrainz-id}?api_key={KEY}`

**Authentication:** API key required (free registration at fanart.tv)

### Response Structure (from sample data)

```json
{
  "name": "Avenged Sevenfold",
  "mbid_id": "24e1b53c-3085-4581-8472-0b0088d2508c",
  "artistbackground": [
    {
      "id": 12345,
      "url": "https://assets.fanart.tv/fanart/music/24e1b53c-.../artistbackground/...",
      "likes": 3
    }
  ],
  "artistthumb": [
    {
      "id": 12346,
      "url": "https://assets.fanart.tv/fanart/music/24e1b53c-.../artistthumb/...",
      "likes": 5
    }
  ],
  "musiclogo": [
    { "id": 12347, "url": "...", "likes": 2 }
  ],
  "hdmusiclogo": [
    { "id": 12348, "url": "...", "likes": 4 }
  ],
  "musicbanner": [
    { "id": 12349, "url": "...", "likes": 1 }
  ],
  "albums": {
    "{album-mbid}": {
      "albumcover": [
        { "id": 12350, "url": "...", "likes": 2 }
      ],
      "cdart": [
        { "id": 12351, "url": "...", "likes": 1, "disc": "1", "size": "1000" }
      ]
    }
  }
}
```

### Image Types Available

| Type | Description | Typical Dimensions | Best Use in Card |
|------|-------------|-------------------|-----------------|
| `artistthumb` | Square artist photo/portrait | 1000x1000 | **Best candidate for card thumbnail** |
| `artistbackground` | Wide landscape background | 1920x1080 | Detail view background |
| `hdmusiclogo` | Transparent HD logo | 800x310 | Decorative only |
| `musiclogo` | Smaller logo | 400x155 | Not useful |
| `musicbanner` | Wide banner | 1000x185 | Not useful for compact card |
| `albums.{id}.albumcover` | Per-album cover art | Various | Fallback if no `artistthumb` |
| `albums.{id}.cdart` | CD disc artwork | Various | Not useful |

### Image Delay Tiers

| Tier | Delay for New Images | Cost |
|------|---------------------|------|
| Project API key | 7 days | Free |
| Personal key | 2 days | Free (with client_key) |
| VIP | Instant | Paid subscription |

### Limitations

1. **API key required** -- Adds a configuration step to Requestarr's config flow
2. **Coverage is not universal** -- Many artists, especially less popular ones, have no fanart.tv entry (returns 404). Estimated 40-60% of searches may return no `artistthumb`.
3. **Additional API call per result** -- For 8 search results, that is 8 parallel fanart.tv calls
4. **Not every artist with a fanart.tv entry has `artistthumb`** -- Some only have logos or backgrounds
5. **Image availability delay** -- New images take 2-7 days to become available

### Key Takeaway for Requestarr

Fanart.tv is a viable source for artist images but adds complexity: another API key to configure, another API to call per result, and unreliable coverage. For v1, **skip direct fanart.tv integration** and instead leverage Lidarr's built-in fanart.tv integration via the Lidarr lookup API (see Section 7). This gives us the same images without requiring a separate API key or additional API calls. For v2, direct fanart.tv could optionally enrich results for popular artists beyond what Lidarr provides.

---

## 6. Music App UX Patterns

### How Streaming Apps Present Artist Search Results

| Platform | Artist Image | Image Shape | Primary Text | Secondary Text | Differentiation from Albums |
|----------|-------------|-------------|-------------|---------------|---------------------------|
| **Spotify** | Artist photo | **Circle** | Artist name (bold, white) | "Artist" type label (grey) | Circle = artist, Square = album/playlist |
| **Apple Music** | Artist photo | **Circle** | Artist name (bold) | "Artist" subtitle | Same circle vs. square convention |
| **YouTube Music** | Channel avatar | **Circle** | Artist/channel name | Subscriber count | Circle = channel/artist |
| **Lidarr** | Poster (fanart.tv) | **Square** (170x250) | Name + year + disambiguation | Rating, type, status labels | N/A (artist-only context) |
| **Ombi** | Poster card | **Portrait rectangle** | Name overlaid on hover | Overview on hover | Type label badge (top-left) |

### Key Pattern: Circular Artist Images

All three major streaming apps use **circular images** for artists to visually distinguish them from albums (which use square images). This is a strong convention users already understand:

- **Circle = Artist/Person/Band**
- **Square = Album/Song/Content**

This convention should be adopted in Requestarr to differentiate Music tab results from Movie/TV tab results (which use rectangular poster thumbnails).

### Text Hierarchy in Music Search Results

Spotify's UX research (analyzed by multiple UX case studies) demonstrates effective text hierarchy:
- **Title** (artist name): Bold, white/primary color, larger size
- **Metadata** (type label): Regular weight, grey/secondary color, smaller size
- **Font size and color differences** allow rapid scanning of result lists

### Fallback Patterns When No Image Available

Music apps handle missing images with these established patterns (in order of preference):

1. **Music note icon** in a colored circle -- most common, immediately signals "music content"
2. **Initials** on a colored/gradient background -- common for user avatars, applicable to artists
3. **Generic silhouette** placeholder -- less visually interesting but functional
4. **Never leave blank** -- empty space breaks the visual rhythm of the list

Best practice: Use a **deterministic color** based on the artist name (hash to color palette) so the same artist always gets the same placeholder color. This provides visual consistency across sessions and gives the list variety.

### Information Density for Compact Cards

For a card constrained to ~300-500px width, the optimal artist search result row layout:

```
+--------+--------------------------------------+----------+
| [Icon] | Artist Name                          | [Action] |
|  48px  | genre tag  |  Group  |  GB           | Request  |
| circle | Disambiguation text (muted)          |  button  |
+--------+--------------------------------------+----------+
```

**Minimum viable (3 elements):** Icon/avatar + Artist name + Request button
**Comfortable (5-6 elements):** Icon + Name + disambiguation/genre + type badge + Request button
**Rich (7+ elements):** All above + country + active years + overview snippet

### Key Takeaway for Requestarr

Follow the streaming app convention: use a **circular placeholder** with a music-note icon or artist initials where no image is available. This communicates "artist" at a glance and distinguishes the Music tab visually from the Movies/TV tabs (which use rectangular poster thumbnails). The list-row format (icon left, text middle, action right) works better than poster-grid for music because artist images are unreliable.

---

## 7. Lidarr API Response Shape

### Artist Lookup Endpoint

**URL:** `GET /api/v1/artist/lookup?term={search_term}`
**Auth:** `X-Api-Key: {lidarr_api_key}` header
**Returns:** Array of Artist objects matching the search term

### Artist Object Fields

Documented from the Go `starr` library (pkg.go.dev/golift.io/starr/lidarr) which provides typed API bindings for Lidarr:

```
Artist {
  id:                int       // Lidarr internal ID (0 for lookup results not yet in library)
  artistName:        string    // Display name
  foreignArtistId:   string    // MusicBrainz artist ID (UUID)
  status:            string    // "continuing" or "ended"
  overview:          string    // Biography text (from metadata provider)
  artistType:        string    // "Group" or "Person"
  disambiguation:    string    // Clarifying text to distinguish same-name artists
  cleanName:         string    // URL-safe normalized name
  sortName:          string    // Sort-friendly name variant
  ended:             bool      // Is the artist inactive/deceased?
  monitored:         bool      // Is Lidarr currently monitoring this artist?

  images:            Image[]   // Array of { url: string, coverType: string }
                               //   coverType values: "poster", "banner", "fanart", "logo"
                               //   URLs point to fanart.tv or cached Lidarr metadata images

  genres:            string[]  // Genre tags (curated, cleaner than MusicBrainz raw tags)
  ratings:           Ratings   // { votes: int, value: float } -- community rating
  links:             Link[]    // External links { url: string, name: string }
  tags:              int[]     // Lidarr tag IDs (internal, not genre tags)

  statistics:        Stats     // Album count, track count, size on disk, etc.
  lastAlbum:         Album     // Most recent album info (title, release date, etc.)
  nextAlbum:         Album     // Upcoming album if known

  qualityProfileId:  int       // Assigned quality profile (0 for lookup results)
  metadataProfileId: int       // Assigned metadata profile (0 for lookup results)
  rootFolderPath:    string    // Storage path (empty for lookup results)
  path:              string    // Full artist path on disk (empty for lookup results)
  added:             datetime  // When added to Lidarr (null for lookup results)

  albumFolder:       bool      // Whether to use album subfolders
  tadbId:            int       // TheAudioDB ID
  discogsId:         int       // Discogs ID

  addOptions: {                // Only needed for POST requests
    monitor:                string  // "all" | "future" | "missing" | "latest" | "first" | "none"
    monitored:              bool
    searchForMissingAlbums: bool
  }
}
```

### Required Fields for POST (Add Artist)

To add a new artist, the minimum required payload is:

```json
{
  "foreignArtistId": "a74b1b7f-71a5-4011-9441-d0b5e4122711",
  "artistName": "Radiohead",
  "qualityProfileId": 1,
  "metadataProfileId": 1,
  "rootFolderPath": "/music",
  "monitored": true,
  "addOptions": {
    "monitor": "all",
    "searchForMissingAlbums": true
  }
}
```

### Lidarr Lookup vs. MusicBrainz Search: Field Comparison

| Field | MusicBrainz Search | Lidarr Lookup | Winner |
|-------|-------------------|---------------|--------|
| Artist name | `name` | `artistName` | Tie |
| MBID | `id` | `foreignArtistId` | Tie |
| Type | `type` ("Group"/"Person") | `artistType` | Tie |
| Disambiguation | `disambiguation` | `disambiguation` | Tie |
| Country | `country` (ISO code) | Not available | MusicBrainz |
| Area | `area.name` (full name) | Not available | MusicBrainz |
| Active from | `life-span.begin` (year) | Not available directly | MusicBrainz |
| Active to | `life-span.end` | Not available | MusicBrainz |
| Is ended | `life-span.ended` (bool) | `ended` / `status` | Tie |
| Tags/genres | `tags[]` (raw, user-voted, noisy) | `genres[]` (curated, clean) | **Lidarr** |
| Overview/bio | **Not available** | `overview` (full biography) | **Lidarr** |
| Images | **Not available** | `images[]` (poster, banner, fanart, logo) | **Lidarr** |
| Rating | Not available | `ratings` { votes, value } | **Lidarr** |
| Album info | Not in search results | `statistics`, `lastAlbum`, `nextAlbum` | **Lidarr** |
| External links | Not in search results | `links[]` | **Lidarr** |
| API key needed | No (free, rate-limited) | Yes (Lidarr instance required) | MusicBrainz |
| Rate limit | 1 req/sec | No external limit (local Lidarr) | **Lidarr** |

### Key Finding: Lidarr Lookup is Superior for Display

**Using Lidarr's `/api/v1/artist/lookup?term=X` instead of MusicBrainz directly provides strictly more data** for display purposes: images (via fanart.tv), overview text, curated genres, ratings, and statistics. The only fields MusicBrainz search provides that Lidarr lookup does not are: country, area, and life-span dates.

Since Requestarr already requires Lidarr to be configured (it is the target for music requests), using Lidarr's lookup endpoint for search is the natural choice -- no additional API configuration needed.

### Key Takeaway for Requestarr

Use Lidarr's artist lookup as the primary search backend for the Music tab. It provides a superset of the display-relevant fields compared to MusicBrainz direct, with the bonus of images and no external rate limiting. MusicBrainz can be used as a supplementary source for country/active-years data in a detail view (v2), but is not needed for v1 search results.

---

## 8. Recommended Music Tab UX Design

### Search Result Card Layout

Unlike Movies/TV tabs which use poster thumbnails (portrait 2:3 rectangle), Music results should use a **list-row layout** optimized for text-heavy content with unreliable images:

```
+------+--------------------------------------+-------------+
|      | Radiohead                            |             |
| [Rh] | alternative rock  |  Group  |  GB    | [ Request ] |
|      | (90s UK grunge band)                 |             |
+------+--------------------------------------+-------------+
|      | On a Friday                          |             |
| [Of] | indie pop  |  Group                  | [ Request ] |
|      | (pre-Radiohead group, until 1991)    |             |
+------+--------------------------------------+-------------+
|      | Metallica                            |  In Library  |
| [Me] | thrash metal  |  Group  |  US        |   (green)    |
|      |                                      |             |
+------+--------------------------------------+-------------+
```

**Left element (48-56px):**
- If Lidarr lookup returned a poster image: circular thumbnail (cropped center)
- If no image: colored circle with 1-2 character initials from artist name
- Circle shape distinguishes from movie/TV poster rectangles (matching Spotify/Apple Music convention)

**Center content:**
- **Line 1:** Artist name (bold, primary text color, 14-16px)
- **Line 2:** Top genre tag (pill badge, muted) + Type badge ("Group"/"Person") + Country code (if available from supplementary data)
- **Line 3:** Disambiguation text (secondary/muted text, 12-13px) -- only shown if present

**Right element:**
- Request button (primary/indigo) -- if not in library and not requested
- OR status badge: "In Library" (green pill) / "Requested" (blue pill) / "Pending" (yellow pill)

### Result Row Height

- **Compact:** 64px (name + genre only, no disambiguation)
- **Standard:** 80px (name + genre + disambiguation)
- **With image:** 80px minimum (image 48px with 16px vertical padding)

**Recommendation:** 80px standard rows showing name, top genre, type, and disambiguation when present. This fits 5-6 results in a typical Lovelace card height of ~480px.

### Click Flow for Music Requests

**Optimal flow (Requestarr Music tab):**
1. Type artist name in search input (submit on Enter or button click)
2. Results appear as list rows (5-8 results)
3. Tap "Request" button directly on result row
4. Inline feedback: button text changes to "Requesting..." (spinner), then becomes "Requested" (blue badge)

**Total: 2 interactions** (type + tap Request). No detail page, no modal, no album selection, no configuration options.

**Comparison with other tools:**

| Tool | Click Count | Flow |
|------|------------|------|
| **Requestarr** | **2** | Type -> Tap Request |
| Lidarr | 3-4 | Type -> Click result -> Configure options -> Click Add |
| Ombi | 4-5 | Type -> Click card -> Navigate detail -> Select albums -> Confirm |
| Aurral | 3-4 | Type -> Click result -> Configure monitoring -> Click Add |

The request adds the artist to Lidarr with "monitor all albums" as the default, matching the household use case where users want the full discography downloaded automatically.

### Handling Missing Images

Since an estimated 40-60% of artists may lack fanart.tv images (especially less popular ones), the placeholder design must be first-class:

```css
/* Initials-based circular placeholder */
.artist-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 16px;
  flex-shrink: 0;
}

/* With image loaded */
.artist-avatar img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}
```

**Deterministic color from artist name** (so the same artist always gets the same color):

```javascript
function avatarColor(name) {
  const colors = [
    '#4f46e5', // indigo
    '#7c3aed', // violet
    '#2563eb', // blue
    '#0891b2', // cyan
    '#059669', // emerald
    '#d97706', // amber
    '#dc2626', // red
    '#db2777', // pink
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

function avatarInitials(name) {
  const words = name.trim().split(/\s+/);
  if (words.length === 1) return words[0].substring(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}
```

### Visual Differentiation from Movies/TV Tabs

| Element | Movies/TV Tabs | Music Tab |
|---------|---------------|-----------|
| Thumbnail shape | Rectangle (2:3 portrait) | Circle (1:1) |
| Thumbnail content | TMDB poster (reliable) | Artist photo or initials placeholder |
| Layout | Poster-centric rows or grid | Text-centric list rows |
| Secondary info | Year, overview snippet | Genre tag, type, country |
| Request target | Specific movie/series | Artist (entire discography) |
| Result row height | ~100px (with 60x90 poster) | ~80px (with 48px circle) |

---

## 9. Implementation Decision Summary

### v1 Implementation: Use Lidarr Lookup as Primary Search

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Search backend | Lidarr `/api/v1/artist/lookup` | Provides images, overview, genres, ratings in one call. No additional API keys. Lidarr already required for requests. |
| Image source | Lidarr `images[]` array (fanart.tv via Lidarr) | Free, no extra config, same quality as Lidarr's own UI |
| Image fallback | Circular placeholder with initials + deterministic color | Handles 40-60% of artists without fanart.tv images |
| Genre display | Lidarr `genres[]` (top 1-2) | Cleaner than MusicBrainz raw tags |
| Card layout | List rows with circle avatar | Works better than poster grid with unreliable images |
| Request model | Artist-level (entire discography) | Matches Lidarr's primary model, simplest UX, 2-click flow |
| Album selection | Deferred to v2 | Album-level requests add significant complexity |
| MusicBrainz direct | Not used in v1 | Lidarr lookup provides superset of display data |
| Fanart.tv direct | Not used | Lidarr handles fanart.tv integration internally |
| Cover Art Archive | Not used in v1 | Too slow (3-hop chain) for search results |

### v2 Enhancements (Post-Validation)

- Album-level requests (select specific albums from an expanded artist detail)
- MusicBrainz supplementary data (country, active years) for detail expansion
- Cover Art Archive album thumbnails in album selection list
- Optional direct fanart.tv integration for richer background images

### Required Lidarr API Calls (Music Tab)

```
Search:      GET  /api/v1/artist/lookup?term={query}
                  -> Returns artist candidates with images, genres, overview

Request:     POST /api/v1/artist
                  -> Body: { foreignArtistId, artistName, qualityProfileId,
                             metadataProfileId, rootFolderPath, monitored: true,
                             addOptions: { monitor: "all", searchForMissingAlbums: true } }

In-Library:  GET  /api/v1/artist
                  -> Returns all artists in Lidarr library (for "already in library" matching)
                  -> Match by foreignArtistId (MBID) against search results

Config:      GET  /api/v1/qualityprofile
             GET  /api/v1/metadataprofile
             GET  /api/v1/rootfolder
                  -> Fetched during config flow, stored in integration config
```

---

## Appendix: Source References

| Source | Location/URL | Confidence |
|--------|-------------|------------|
| MusicBrainz API search docs | https://musicbrainz.org/doc/MusicBrainz_API/Search | HIGH |
| MusicBrainz live API response | Verified via `curl` for Radiohead (2026-02-23) | HIGH |
| Cover Art Archive API docs | https://musicbrainz.org/doc/Cover_Art_Archive/API | HIGH |
| Fanart.tv API docs | https://fanarttv.docs.apiary.io/ | MEDIUM |
| Fanart.tv sample response | github.com/Omertron/api-fanarttv `sample/music_artist.json` | HIGH |
| Lidarr `AddNewArtistSearchResult.js` | github.com/Lidarr/Lidarr `frontend/src/Search/Artist/` | HIGH |
| Lidarr `AddNewArtistModalContent.js` | github.com/Lidarr/Lidarr `frontend/src/Search/Artist/` | HIGH |
| Lidarr `AddArtistOptionsForm.js` | github.com/Lidarr/Lidarr `frontend/src/Search/Common/` | HIGH |
| Lidarr `AddNewArtistSearchResult.css` | github.com/Lidarr/Lidarr `frontend/src/Search/Artist/` | HIGH |
| Lidarr Artist struct (Go starr lib) | https://pkg.go.dev/golift.io/starr/lidarr | HIGH |
| Ombi `ISearchMusicResult.ts` (V1) | github.com/Ombi-app/Ombi `ClientApp/src/app/interfaces/` | HIGH |
| Ombi `IMusicSearchResultV2.ts` (V2) | github.com/Ombi-app/Ombi `ClientApp/src/app/interfaces/` | HIGH |
| Ombi `ArtistInformation.cs` model | github.com/Ombi-app/Ombi `Ombi.Core/Models/Search/V2/Music/` | HIGH |
| Ombi `MusicSearchEngineV2.cs` | github.com/Ombi-app/Ombi `Ombi.Core/Engine/V2/` | HIGH |
| Ombi artist detail template | github.com/Ombi-app/Ombi `media-details/components/artist/` | HIGH |
| Ombi artist info panel | github.com/Ombi-app/Ombi `artist/panels/artist-information-panel/` | HIGH |
| Ombi discover card template | github.com/Ombi-app/Ombi `discover/components/card/` | HIGH |
| Ombi music requests template | github.com/Ombi-app/Ombi `requests/music/` | HIGH |
| Ombi music UX issues | github.com/Ombi-app/Ombi #4941, #4271, #3027, #2805, #4608, #2549, #4809 | MEDIUM |
| Aurral project | https://github.com/lklynet/aurral | MEDIUM |
| Spotify UX analysis | abdulazizahwan.com, uxdesign.cc, uxplanet.org | MEDIUM |
| Music app placeholder patterns | uxplanet.org, uxpin.com, setproduct.com | MEDIUM |

---

*Music Tab UX research for: Requestarr (Home Assistant HACS media request card)*
*Researched: 2026-02-23*
