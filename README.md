# Requestarr

A Home Assistant HACS integration for searching and requesting media through your *arr stack (Radarr, Sonarr, Lidarr) with TMDB search, all from a Lovelace dashboard card.

## Features

- Search movies, TV shows, and music via TMDB
- Request media directly to Radarr, Sonarr, or Lidarr
- Library count sensors for each connected service
- Tabbed Lovelace card with search, results, and request buttons
- Multi-step config flow: TMDB > Radarr > Sonarr > Lidarr
- Visual card editor

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "Requestarr" and install
3. Restart Home Assistant
4. Add the integration via Settings > Devices & Services

### Manual

1. Copy `custom_components/requestarr/` to your HA `config/custom_components/`
2. Restart Home Assistant
3. Add the integration via Settings > Devices & Services

## Configuration

The config flow walks through four steps:

1. **TMDB API Key** (required) - Get a free key at [themoviedb.org](https://www.themoviedb.org/settings/api)
2. **Radarr** (optional) - URL and API key for movie requests
3. **Sonarr** (optional) - URL and API key for TV show requests
4. **Lidarr** (optional) - URL and API key for music requests

## Card

Add the Requestarr card to any dashboard. It provides:

- **Tabs**: Switch between Movies, TV Shows, and Music
- **Search**: Search TMDB for media
- **Results**: Browse results with posters, titles, and descriptions
- **Request**: One-click request to the appropriate *arr service
- **Stats**: Library counts from connected services

## Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.requestarr_radarr_movies` | Number of movies in Radarr |
| `sensor.requestarr_sonarr_series` | Number of series in Sonarr |
| `sensor.requestarr_lidarr_artists` | Number of artists in Lidarr |

## License

MIT
