# Arr Lookup API Research: Can We Use Arr Services as the Primary Search Data Source?

**Domain:** Home Assistant HACS integration -- media request management
**Researched:** 2026-02-23
**Confidence:** HIGH (verified against Radarr/Sonarr/Lidarr source code on GitHub `develop` branches)

## Executive Summary

**Yes, the arr lookup endpoints can fully replace direct TMDB and MusicBrainz calls for search.** Each arr service provides a lookup endpoint that returns rich metadata including images, overview, year, genres, and ratings -- everything needed for a search result card. The images are either direct CDN URLs (for items not in your library) or proxied through the arr service's own `/MediaCoverProxy/` endpoint. This eliminates the need for a TMDB API key and a separate MusicBrainz client in the HA backend.

### Key Decision

| Approach | TMDB + MusicBrainz Direct | Arr Lookup Endpoints |
|----------|--------------------------|---------------------|
| API clients needed | 3 (TMDB, MusicBrainz, arr services) | 1 (arr services only) |
| API keys needed | TMDB key + arr keys | Arr keys only |
| Config flow steps | TMDB step + 3 arr steps | 3 arr steps only |
| Image source | TMDB CDN (direct, no auth) | Arr proxy OR direct CDN |
| TVDB ID mapping for Sonarr | Extra TMDB API call needed | Not needed (Sonarr returns tvdbId) |
| MusicBrainz rate limiting | 1 req/sec, must implement | Not our problem (Lidarr handles it) |
| Search quality | TMDB/MB native search | Same data, same search quality |

**Recommendation: Use arr lookup endpoints as the primary search API.**

---

## Radarr v3 -- Movie Lookup

### Endpoint: `GET /api/v3/movie/lookup?term={query}`

Returns an array of `MovieResource` objects. Each result includes full metadata sourced from TMDB behind the scenes.

#### Response Fields (from `MovieResource.cs`)

```json
{
  "title": "Interstellar",
  "originalTitle": "Interstellar",
  "sortTitle": "interstellar",
  "status": "released",
  "overview": "The adventures of a group of explorers who make use of a newly discovered wormhole...",
  "inCinemas": "2014-11-05T00:00:00Z",
  "physicalRelease": "2015-03-31T00:00:00Z",
  "images": [
    {
      "coverType": "poster",
      "url": "/MediaCoverProxy/<sha256hash>/nBNZadXqJSdt05SHLqgT0HuC5Gm.jpg",
      "remoteUrl": "https://image.tmdb.org/t/p/original/nBNZadXqJSdt05SHLqgT0HuC5Gm.jpg"
    },
    {
      "coverType": "fanart",
      "url": "/MediaCoverProxy/<sha256hash>/xJHokMbljXjADYdit5fK1EVF.jpg",
      "remoteUrl": "https://image.tmdb.org/t/p/original/xJHokMbljXjADYdit5fK1EVF.jpg"
    }
  ],
  "remotePoster": "https://image.tmdb.org/t/p/original/nBNZadXqJSdt05SHLqgT0HuC5Gm.jpg",
  "website": "http://www.interstellarmovie.net/",
  "year": 2014,
  "studio": "Paramount",
  "runtime": 169,
  "imdbId": "tt0816692",
  "tmdbId": 157336,
  "titleSlug": "interstellar-157336",
  "certification": "PG-13",
  "genres": ["Adventure", "Drama", "Science Fiction"],
  "ratings": {
    "imdb": { "votes": 2000000, "value": 8.7, "type": "user" },
    "tmdb": { "votes": 35000, "value": 8.4, "type": "user" },
    "metacritic": { "votes": 0, "value": 74, "type": "critic" },
    "rottenTomatoes": { "votes": 0, "value": 73, "type": "critic" }
  },
  "collection": { "title": "...", "tmdbId": 0 },
  "youTubeTrailerId": "zSWdZVtXT7E",
  "id": 0
}
```

#### Available MediaCoverTypes (shared across all arr services)

| CoverType | Description |
|-----------|-------------|
| `poster` | Movie poster (portrait, ~680x1000) |
| `fanart` | Background/backdrop (landscape, ~1920x1080) |
| `banner` | Wide banner (landscape, ~758x140) |
| `screenshot` | Screenshot from media |
| `headshot` | Person headshot |
| `clearlogo` | Transparent logo (.png) |

#### Additional Lookup Endpoints

- `GET /api/v3/movie/lookup/tmdb?tmdbId={id}` -- Lookup by TMDB ID (returns single `MovieResource`)
- `GET /api/v3/movie/lookup/imdb?imdbId={id}` -- Lookup by IMDB ID (returns single `MovieResource`)

#### Image URL Behavior for Lookup Results

When `movieId == 0` (movie NOT in Radarr library), the `ConvertToLocalUrls` method in `MediaCoverService.cs` registers the remote URL with `MediaCoverProxy` and rewrites the `url` field:

```
Original remote URL: https://image.tmdb.org/t/p/original/nBNZadXqJSdt05SHLqgT0HuC5Gm.jpg
Rewritten to:        /MediaCoverProxy/<sha256-of-url>/nBNZadXqJSdt05SHLqgT0HuC5Gm.jpg
```

The `remoteUrl` field retains the original TMDB CDN URL. The `remotePoster` top-level field also contains the direct TMDB CDN URL.

When `movieId > 0` (movie IS in Radarr library), the URL points to the local cached file:
```
/MediaCover/42/poster.jpg?lastWrite=638416459200000000
```

#### Ratings Structure (Radarr v3 -- richer than v2)

```csharp
public class Ratings {
    public RatingChild Imdb { get; set; }
    public RatingChild Tmdb { get; set; }
    public RatingChild Metacritic { get; set; }
    public RatingChild RottenTomatoes { get; set; }
    public RatingChild Trakt { get; set; }
}
public class RatingChild {
    public int Votes { get; set; }
    public decimal Value { get; set; }
    public RatingType Type { get; set; } // User or Critic
}
```

This is **richer** than what TMDB returns directly -- we get IMDB, TMDB, Metacritic, Rotten Tomatoes, and Trakt ratings in one call.

---

## Sonarr v3 -- Series Lookup

### Endpoint: `GET /api/v3/series/lookup?term={query}`

Returns an array of `SeriesResource` objects. Sonarr sources metadata from TheTVDB (and also maintains TMDB IDs).

#### Response Fields (from `SeriesResource.cs`)

```json
{
  "title": "Game of Thrones",
  "sortTitle": "game of thrones",
  "status": "ended",
  "ended": true,
  "overview": "Seven noble families fight for control of the mythical land of Westeros...",
  "network": "HBO",
  "airTime": "21:00",
  "images": [
    {
      "coverType": "poster",
      "url": "/MediaCoverProxy/<sha256hash>/121361-4.jpg",
      "remoteUrl": "https://artworks.thetvdb.com/banners/posters/121361-4.jpg"
    },
    {
      "coverType": "banner",
      "url": "/MediaCoverProxy/<sha256hash>/graphical/121361-g19.jpg",
      "remoteUrl": "https://artworks.thetvdb.com/banners/graphical/121361-g19.jpg"
    },
    {
      "coverType": "fanart",
      "url": "/MediaCoverProxy/<sha256hash>/fanart/original/121361-15.jpg",
      "remoteUrl": "https://artworks.thetvdb.com/banners/fanart/original/121361-15.jpg"
    }
  ],
  "remotePoster": "https://artworks.thetvdb.com/banners/posters/121361-4.jpg",
  "originalLanguage": { "id": 1, "name": "English" },
  "seasons": [
    { "seasonNumber": 0, "monitored": false },
    { "seasonNumber": 1, "monitored": true }
  ],
  "year": 2011,
  "runtime": 60,
  "tvdbId": 121361,
  "tvMazeId": 82,
  "tmdbId": 1399,
  "imdbId": "tt0944947",
  "certification": "TV-MA",
  "genres": ["Action", "Adventure", "Drama", "Fantasy"],
  "ratings": { "votes": 1254, "value": 9.4 },
  "seriesType": "standard",
  "firstAired": "2011-04-17T00:00:00Z",
  "lastAired": "2019-05-19T00:00:00Z",
  "id": 0
}
```

#### TVDB ID Mapping -- Eliminated

A critical advantage: Sonarr's lookup returns `tvdbId`, `tmdbId`, and `imdbId` in the response. When using TMDB directly for search, we would need an extra API call (`/tv/{tmdb_id}/external_ids`) to get the `tvdbId` before adding to Sonarr. With the Sonarr lookup endpoint, the `tvdbId` is already present.

#### Image Sources

Sonarr images come from TheTVDB:
- Posters: `https://artworks.thetvdb.com/banners/posters/{tvdbId}-{n}.jpg`
- Banners: `https://artworks.thetvdb.com/banners/graphical/{tvdbId}-g{n}.jpg`
- Fanart: `https://artworks.thetvdb.com/banners/fanart/original/{tvdbId}-{n}.jpg`

Same proxy mechanism as Radarr -- lookup results (id=0) use `MediaCoverProxy`, library items use local `MediaCover` paths.

#### Additional Lookup Methods

- `GET /api/v3/series/lookup?term=tvdb:{tvdbId}` -- Lookup by TVDB ID
- `GET /api/v3/series/lookup?term=tmdb:{tmdbId}` -- Lookup by TMDB ID (if supported in current version)

#### Ratings Structure (Sonarr -- simpler)

```csharp
public class Ratings {
    public int Votes { get; set; }
    public decimal Value { get; set; }
}
```

Sonarr's ratings are simpler than Radarr's -- a single votes/value pair (from TheTVDB). Still sufficient for display.

---

## Lidarr v1 -- Artist and Album Lookup

### Endpoint: `GET /api/v1/artist/lookup?term={query}`

Returns an array of `ArtistResource` objects. Lidarr sources metadata from its own metadata server (LidarrAPI), which aggregates MusicBrainz, fanart.tv, and other sources.

#### Response Fields (from `ArtistResource.cs`)

```json
{
  "artistName": "Radiohead",
  "sortName": "radiohead",
  "status": "active",
  "overview": "Radiohead are an English rock band formed in Abingdon, Oxfordshire...",
  "artistType": "Group",
  "disambiguation": "",
  "images": [
    {
      "coverType": "poster",
      "url": "/MediaCoverProxy/<sha256hash>/artist-poster.jpg",
      "remoteUrl": "https://assets.fanart.tv/fanart/music/..."
    },
    {
      "coverType": "fanart",
      "url": "/MediaCoverProxy/<sha256hash>/artist-fanart.jpg",
      "remoteUrl": "https://assets.fanart.tv/fanart/music/..."
    },
    {
      "coverType": "banner",
      "url": "/MediaCoverProxy/<sha256hash>/artist-banner.jpg",
      "remoteUrl": "https://assets.fanart.tv/fanart/music/..."
    },
    {
      "coverType": "logo",
      "url": "/MediaCoverProxy/<sha256hash>/artist-logo.png",
      "remoteUrl": "https://assets.fanart.tv/fanart/music/..."
    }
  ],
  "remotePoster": "https://assets.fanart.tv/fanart/music/...",
  "foreignArtistId": "a74b1b7f-71a5-4011-9441-d0b5e4122711",
  "tadbId": 0,
  "discogsId": 0,
  "genres": ["Alternative Rock", "Art Rock", "Electronic"],
  "ratings": { "votes": 0, "value": 0.0 },
  "links": [
    { "url": "https://www.radiohead.com", "name": "Official Site" },
    { "url": "https://open.spotify.com/artist/...", "name": "Spotify" }
  ],
  "id": 0
}
```

### Endpoint: `GET /api/v1/album/lookup?term={query}`

Returns an array of `AlbumResource` objects.

#### Album Response Fields (from `AlbumResource.cs`)

```json
{
  "title": "OK Computer",
  "disambiguation": "",
  "overview": "OK Computer is the third studio album...",
  "artistId": 0,
  "foreignAlbumId": "b1392450-e666-3926-a536-22c65f834433",
  "albumType": "Album",
  "secondaryTypes": [],
  "images": [
    {
      "coverType": "cover",
      "url": "/MediaCoverProxy/<sha256hash>/cover.jpg",
      "remoteUrl": "https://coverartarchive.org/release/..."
    }
  ],
  "remoteCover": "https://coverartarchive.org/release/.../front-500.jpg",
  "genres": ["Alternative Rock"],
  "ratings": { "votes": 0, "value": 0.0 },
  "releaseDate": "1997-05-21T00:00:00Z",
  "duration": 3200000,
  "links": [],
  "artist": { /* embedded ArtistResource */ },
  "media": [{ "mediumNumber": 1, "mediumName": "CD", "mediumFormat": "CD" }],
  "id": 0
}
```

### Endpoint: `GET /api/v1/search?term={query}`

Returns a **unified** `SearchResource` array combining both artist AND album results:

```json
[
  {
    "foreignId": "a74b1b7f-71a5-4011-9441-d0b5e4122711",
    "artist": { /* full ArtistResource */ },
    "album": null,
    "id": 1
  },
  {
    "foreignId": "b1392450-e666-3926-a536-22c65f834433",
    "artist": null,
    "album": { /* full AlbumResource with embedded artist */ },
    "id": 2
  }
]
```

This is ideal for our use case -- a single call returns both artist and album matches.

#### Lidarr MediaCoverTypes (extended)

| CoverType | Description |
|-----------|-------------|
| `poster` | Artist poster (from fanart.tv) |
| `banner` | Artist banner (from fanart.tv) |
| `fanart` | Artist background (from fanart.tv) |
| `cover` | Album cover art (from Cover Art Archive / MusicBrainz) |
| `disc` | Disc image (from fanart.tv) |
| `logo` | Artist logo (from fanart.tv) |
| `clearlogo` | Transparent logo |
| `headshot` | Person headshot |

#### Image Sources

- **Artist images:** Sourced from **fanart.tv** (posters, banners, fanart, logos)
- **Album cover art:** Sourced from **Cover Art Archive** (MusicBrainz)
- Both go through the same `MediaCoverProxy` mechanism for lookup results

#### Caveat: Missing Artist Images

Many artists (especially less popular ones) have no images on fanart.tv. This is a known limitation of Lidarr. Album cover art from Cover Art Archive has better coverage since MusicBrainz has broader community contributions.

---

## Image Accessibility and Authentication

### How the MediaCoverProxy Works

Source: `NzbDrone.Core/MediaCover/MediaCoverProxy.cs` (shared codebase)

1. When a lookup result has `id == 0` (not in library), `ConvertToLocalUrls()` calls `MediaCoverProxy.RegisterUrl(remoteUrl)`
2. `RegisterUrl()` computes `SHA256(remoteUrl)`, caches the mapping for **24 hours**, and returns a local path:
   ```
   /{UrlBase}/MediaCoverProxy/{sha256hash}/{filename}
   ```
3. When a browser requests this URL, the arr service fetches the remote image on-demand and returns the bytes

### Authentication Requirements

| Endpoint Pattern | Auth Required | Method |
|------------------|---------------|--------|
| `/api/v3/movie/lookup?term=X` | YES | `X-Api-Key` header or `?apikey=KEY` query param |
| `/api/v3/MediaCover/{id}/poster.jpg` | YES | `X-Api-Key` header or `?apikey=KEY` query param |
| `/MediaCoverProxy/{hash}/{filename}` | YES | `X-Api-Key` header or `?apikey=KEY` query param |
| Direct CDN URLs (`image.tmdb.org`, `artworks.thetvdb.com`, `assets.fanart.tv`, `coverartarchive.org`) | NO | Public CDN, no auth needed |

The `MediaCoverController` is decorated with `[V3ApiController]` which implies API authentication. The `MediaCoverProxy` endpoint also requires authentication (it's behind the same middleware).

### Critical Implication for the HA Card

The Lovelace card's browser **cannot directly fetch** images from `http://192.168.50.250:7878/MediaCoverProxy/{hash}/poster.jpg` in an `<img>` tag because:

1. `<img>` tags cannot send custom `X-Api-Key` headers
2. You would need to append `?apikey=KEY` to the URL, which **exposes the API key in the HTML source**

### Solution: Use `remoteUrl` / `remotePoster` Fields Directly

The arr lookup responses include **both** the proxied URL and the original remote URL:

| Field | Value | Auth needed? |
|-------|-------|-------------|
| `images[].url` | `/MediaCoverProxy/{hash}/poster.jpg` | YES (arr API key) |
| `images[].remoteUrl` | `https://image.tmdb.org/t/p/original/abc.jpg` | NO (public CDN) |
| `remotePoster` | `https://image.tmdb.org/t/p/original/abc.jpg` | NO (public CDN) |

**The `remoteUrl` and `remotePoster` fields point to public CDN URLs that require no authentication.** These can be used directly in `<img>` tags.

| Service | Image CDN | Auth | CORS |
|---------|-----------|------|------|
| Radarr (movies) | `https://image.tmdb.org/t/p/original/` | None | Yes, TMDB allows cross-origin |
| Sonarr (TV) | `https://artworks.thetvdb.com/banners/` | None | Yes |
| Lidarr (artists) | `https://assets.fanart.tv/fanart/music/` | None | Yes |
| Lidarr (albums) | `https://coverartarchive.org/release/` | None | Yes |

### Alternative: Proxy Through HA Backend

If we prefer not to have the card's browser make direct requests to external CDNs (privacy concern, or for environments without internet access from the browser), we can have the HA backend fetch images from the arr service's proxy endpoint (using the API key server-side) and serve them via an HA endpoint. However, this adds complexity and is not needed for the typical LAN setup.

---

## Architecture Simplification Analysis

### Before (TMDB + MusicBrainz + arr services)

```
Card --WS--> HA Backend --HTTP--> TMDB /search/movie (needs TMDB key)
                        --HTTP--> TMDB /search/tv (needs TMDB key)
                        --HTTP--> TMDB /tv/{id}/external_ids (to get tvdbId for Sonarr!)
                        --HTTP--> MusicBrainz /ws/2/artist (rate limited 1/sec, needs User-Agent)
                        --HTTP--> Radarr /api/v3/movie (to add)
                        --HTTP--> Sonarr /api/v3/series (to add)
                        --HTTP--> Lidarr /api/v1/artist (to add)

Config flow: 4 steps (TMDB key, Radarr, Sonarr, Lidarr)
API clients: 3 separate patterns
Image URLs: TMDB CDN (direct from browser)
Sonarr add: requires extra TMDB API call for tvdbId mapping
```

### After (arr services only)

```
Card --WS--> HA Backend --HTTP--> Radarr /api/v3/movie/lookup (search + metadata)
                        --HTTP--> Sonarr /api/v3/series/lookup (search + metadata)
                        --HTTP--> Lidarr /api/v1/search (search + metadata, artists AND albums)
                        --HTTP--> Radarr /api/v3/movie (to add)
                        --HTTP--> Sonarr /api/v3/series (to add)
                        --HTTP--> Lidarr /api/v1/artist (to add)

Config flow: 3 steps (Radarr, Sonarr, Lidarr) -- NO TMDB key step
API clients: 1 pattern (all arr services use same X-Api-Key auth)
Image URLs: remoteUrl fields --> public CDN (direct from browser)
Sonarr add: tvdbId already in lookup response -- no extra call needed!
MusicBrainz rate limiting: handled by Lidarr internally, not our problem
```

### What We Gain

1. **No TMDB API key needed** -- Users do not need to register at TMDB for a free API key. One fewer config step, one fewer thing that can go wrong.

2. **No MusicBrainz client** -- No need to implement User-Agent handling, rate limiting (1 req/sec), or the complex MusicBrainz query syntax. Lidarr handles all of this internally.

3. **No TVDB ID mapping** -- Sonarr's lookup already returns `tvdbId`. The extra TMDB `/tv/{id}/external_ids` call is eliminated.

4. **Uniform API pattern** -- All three services use the same auth pattern (`X-Api-Key` header). The coordinator code becomes a simple loop over configured services.

5. **Richer metadata** -- Radarr returns IMDB, TMDB, Metacritic, RT, and Trakt ratings in one call. TMDB alone only returns its own rating.

6. **Direct add compatibility** -- Lookup results return the exact IDs needed to POST back to the same service (tmdbId for Radarr, tvdbId for Sonarr, foreignArtistId/foreignAlbumId for Lidarr).

7. **"Already in library" detection** -- If a lookup result has `id > 0`, it's already in the library. No separate check needed.

### What We Lose

1. **Multi-source search** -- TMDB search may return slightly different results than Radarr's search (which goes through Radarr's own metadata server, RadarrAPI.TMDB). In practice, results are equivalent since Radarr uses TMDB as its source.

2. **Independence from arr services** -- If Radarr is down, movie search is also down. With TMDB direct, search would still work even if Radarr was temporarily unavailable (though you couldn't add the movie anyway).

3. **Poster size control** -- TMDB offers multiple sizes (`/w185/`, `/w342/`, `/w500/`, `/original/`). The arr lookup returns only `/original/` in `remoteUrl`. We can rewrite the URL path to get smaller sizes:
   ```
   Original: https://image.tmdb.org/t/p/original/abc.jpg
   Smaller:  https://image.tmdb.org/t/p/w342/abc.jpg
   ```
   TheTVDB and fanart.tv also support size parameters in some cases.

---

## Recommended Image Strategy

### For the Lovelace Card

Use the `remoteUrl` or `remotePoster` field directly in `<img>` tags. For TMDB images, rewrite the URL to request a smaller size:

```javascript
function getImageUrl(result, mediaType) {
  // Prefer remotePoster (top-level field, always the poster)
  let url = result.remotePoster || result.remoteCover;

  // Fallback: find poster/cover in images array
  if (!url && result.images) {
    const posterType = mediaType === 'music' ? 'cover' : 'poster';
    const img = result.images.find(i => i.coverType === posterType);
    url = img?.remoteUrl || img?.url;
  }

  // For TMDB images, request w342 instead of original for faster loading
  if (url && url.includes('image.tmdb.org/t/p/original')) {
    url = url.replace('/t/p/original/', '/t/p/w342/');
  }

  return url;
}
```

### For the HA Backend (coordinator)

Extract and normalize the image URL when building the search result response:

```python
def _normalize_result(self, item: dict, media_type: str) -> dict:
    """Normalize arr lookup result into a standard search result dict."""
    poster_url = item.get("remotePoster") or item.get("remoteCover")

    if not poster_url and "images" in item:
        cover_type = "cover" if media_type == "music" else "poster"
        for img in item["images"]:
            if img.get("coverType") == cover_type:
                poster_url = img.get("remoteUrl") or img.get("url")
                break

    # Downsize TMDB images for faster card rendering
    if poster_url and "image.tmdb.org/t/p/original" in poster_url:
        poster_url = poster_url.replace("/t/p/original/", "/t/p/w342/")

    return {
        "id": item.get("tmdbId") or item.get("tvdbId") or item.get("foreignArtistId") or item.get("foreignAlbumId"),
        "title": item.get("title") or item.get("artistName"),
        "year": item.get("year") or (item.get("releaseDate", "")[:4] if item.get("releaseDate") else None),
        "overview": item.get("overview", ""),
        "poster_url": poster_url,
        "genres": item.get("genres", []),
        "ratings": item.get("ratings"),
        "media_type": media_type,
        "in_library": item.get("id", 0) > 0,
        # IDs needed for adding to arr service
        "tmdb_id": item.get("tmdbId"),
        "tvdb_id": item.get("tvdbId"),
        "imdb_id": item.get("imdbId"),
        "foreign_artist_id": item.get("foreignArtistId"),
        "foreign_album_id": item.get("foreignAlbumId"),
    }
```

---

## API Endpoint Summary

### Search Endpoints

| Service | Endpoint | Auth | Returns |
|---------|----------|------|---------|
| Radarr | `GET /api/v3/movie/lookup?term={query}` | `X-Api-Key` | `MovieResource[]` |
| Radarr | `GET /api/v3/movie/lookup/tmdb?tmdbId={id}` | `X-Api-Key` | `MovieResource` |
| Radarr | `GET /api/v3/movie/lookup/imdb?imdbId={id}` | `X-Api-Key` | `MovieResource` |
| Sonarr | `GET /api/v3/series/lookup?term={query}` | `X-Api-Key` | `SeriesResource[]` |
| Sonarr | `GET /api/v3/series/lookup?term=tvdb:{tvdbId}` | `X-Api-Key` | `SeriesResource[]` |
| Lidarr | `GET /api/v1/artist/lookup?term={query}` | `X-Api-Key` | `ArtistResource[]` |
| Lidarr | `GET /api/v1/album/lookup?term={query}` | `X-Api-Key` | `AlbumResource[]` |
| Lidarr | `GET /api/v1/search?term={query}` | `X-Api-Key` | `SearchResource[]` (artists + albums mixed) |

### Add Endpoints

| Service | Endpoint | Auth | Key Fields Required |
|---------|----------|------|-------------------|
| Radarr | `POST /api/v3/movie` | `X-Api-Key` | `tmdbId`, `qualityProfileId`, `rootFolderPath`, `title`, `titleSlug` |
| Sonarr | `POST /api/v3/series` | `X-Api-Key` | `tvdbId`, `qualityProfileId`, `rootFolderPath`, `title`, `titleSlug` |
| Lidarr | `POST /api/v1/artist` | `X-Api-Key` | `foreignArtistId`, `qualityProfileId`, `metadataProfileId`, `rootFolderPath` |

### Metadata Richness Comparison

| Field | Radarr Lookup | Sonarr Lookup | Lidarr Lookup | TMDB Direct | MB Direct |
|-------|--------------|--------------|--------------|-------------|-----------|
| Title | Y | Y | Y | Y | Y |
| Year | Y | Y | Y (releaseDate) | Y | Y |
| Overview | Y | Y | Y | Y | N (limited) |
| Poster URL | Y (TMDB CDN) | Y (TVDB CDN) | Y (fanart.tv/CAA) | Y (TMDB CDN) | N |
| Fanart URL | Y (TMDB CDN) | Y (TVDB CDN) | Y (fanart.tv) | Y (TMDB CDN) | N |
| Genres | Y | Y | Y | Y | Partial |
| Ratings | Y (multi-source) | Y (single) | Limited | Y (TMDB only) | N |
| Runtime | Y | Y | Y (duration) | Y | N |
| Studio/Network | Y | Y | N | Y | N |
| Certification | Y | Y | N | Y | N |
| External IDs | tmdb, imdb | tvdb, tmdb, imdb, tvmaze | mbid, discogs, tadb | tmdb only | mbid only |
| In-library flag | Y (id > 0) | Y (id > 0) | Y (id > 0) | N | N |

---

## Sources

- Radarr MovieResource.cs: https://github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/Movies/MovieResource.cs
- Radarr MovieLookupController.cs: https://github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/Movies/MovieLookupController.cs
- Radarr MediaCoverProxy.cs: https://github.com/Radarr/Radarr/blob/develop/src/NzbDrone.Core/MediaCover/MediaCoverProxy.cs
- Radarr MediaCoverService.cs: https://github.com/Radarr/Radarr/blob/develop/src/NzbDrone.Core/MediaCover/MediaCoverService.cs
- Radarr MediaCoverController.cs: https://github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/MediaCovers/MediaCoverController.cs
- Radarr MediaCover.cs (types): https://github.com/Radarr/Radarr/blob/develop/src/NzbDrone.Core/MediaCover/MediaCover.cs
- Radarr Ratings.cs: https://github.com/Radarr/Radarr/blob/develop/src/NzbDrone.Core/Movies/Ratings.cs
- Sonarr SeriesResource.cs: https://github.com/Sonarr/Sonarr/blob/develop/src/Sonarr.Api.V3/Series/SeriesResource.cs
- Sonarr SeriesLookupController.cs: https://github.com/Sonarr/Sonarr/blob/develop/src/Sonarr.Api.V3/Series/SeriesLookupController.cs
- Sonarr MediaCover.cs: https://github.com/Sonarr/Sonarr/blob/develop/src/NzbDrone.Core/MediaCover/MediaCover.cs
- Sonarr MediaCoverService.cs: https://github.com/Sonarr/Sonarr/blob/develop/src/NzbDrone.Core/MediaCover/MediaCoverService.cs
- Sonarr image auth discussion: https://forums.sonarr.tv/t/access-images-using-api-key/9244
- Sonarr MediaCover auth issue: https://github.com/Sonarr/Sonarr/issues/291
- Lidarr ArtistResource.cs: https://github.com/Lidarr/Lidarr/blob/develop/src/Lidarr.Api.V1/Artist/ArtistResource.cs
- Lidarr ArtistLookupController.cs: https://github.com/Lidarr/Lidarr/blob/develop/src/Lidarr.Api.V1/Artist/ArtistLookupController.cs
- Lidarr AlbumResource.cs: https://github.com/Lidarr/Lidarr/blob/develop/src/Lidarr.Api.V1/Albums/AlbumResource.cs
- Lidarr AlbumLookupController.cs: https://github.com/Lidarr/Lidarr/blob/develop/src/Lidarr.Api.V1/Albums/AlbumLookupController.cs
- Lidarr SearchController.cs: https://github.com/Lidarr/Lidarr/blob/develop/src/Lidarr.Api.V1/Search/SearchController.cs
- Lidarr SearchResource.cs: https://github.com/Lidarr/Lidarr/blob/develop/src/Lidarr.Api.V1/Search/SearchResource.cs
- Lidarr MediaCover.cs (types): https://github.com/Lidarr/Lidarr/blob/develop/src/NzbDrone.Core/MediaCover/MediaCover.cs
- Lidarr MediaCoverService.cs: https://github.com/Lidarr/Lidarr/blob/develop/src/NzbDrone.Core/MediaCover/MediaCoverService.cs
- Lidarr FAQ (image sources): https://wiki.servarr.com/lidarr/faq
- Radarr image URL issue: https://github.com/Radarr/Radarr/issues/1311
- Radarr RemotePoster fix: https://github.com/Radarr/Radarr/issues/4729
- Radarr API Docs: https://radarr.video/docs/api/
- Sonarr API Docs: https://sonarr.tv/docs/api/
- Lidarr API Docs: https://lidarr.audio/docs/api/
- Existing HA integrations: https://github.com/custom-components/sensor.radarr_upcoming_media, https://github.com/Vansmak/mediarr-card

---
*Arr Lookup API research for: Requestarr -- Home Assistant HACS media request integration*
*Researched: 2026-02-23*
