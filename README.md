# Requestarr

HA-native media request dashboard for Radarr, Sonarr, and Lidarr.

[![HACS Default](https://img.shields.io/badge/HACS-Default-blue.svg)](https://github.com/hacs/integration)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2025.7%2B-blue.svg)](https://www.home-assistant.io/)

Search for movies, TV shows, and music artists from a Home Assistant dashboard card and send requests directly to your arr stack — no separate app, no extra auth, no extra container.

## Features

- **Movies**: Search Radarr by title, request with one tap. "In Library" badge if already in Radarr.
- **TV**: Search Sonarr by title, request with one tap. "In Library" badge if already in Sonarr.
- **Music**: Search Lidarr by artist name, request with one tap. Circular avatar thumbnails (Spotify convention).
- All three services are optional — only configure what you have.
- Arr API keys stay server-side. Only public CDN image URLs (TMDB, TheTVDB, fanart.tv) reach the browser.

## Requirements

- Home Assistant 2025.7+
- At least one arr service: Radarr, Sonarr, and/or Lidarr
- HACS (for managed install) or manual file copy

## Installation via HACS

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Search for **Requestarr**
4. Click Install and restart Home Assistant

## Manual Installation

1. Copy `custom_components/requestarr/` into your HA `config/custom_components/`
2. Restart Home Assistant
3. Add the integration via **Settings → Devices & Services → Add Integration → Requestarr**

## Configuration

The setup wizard walks through three optional steps — Radarr, Sonarr, Lidarr. At least one must be configured.

For each service, provide:
- **URL** — e.g. `http://192.168.1.50:7878`
- **API Key** — from the arr service Settings → General → Security

Quality profiles, root folders, and (for Lidarr) metadata profiles are fetched automatically at setup time.

### Options

After setup, go to **Settings → Devices & Services → Requestarr → Configure** to:
- Change the default quality profile or root folder per service
- Toggle SSL verification
- Refresh profiles if you've changed them in the arr service

## Adding the Card

In your Lovelace dashboard, add a **Custom: Requestarr Card**:

```yaml
type: custom:requestarr-card
header: "Media Requests"
show_radarr: true
show_sonarr: true
show_lidarr: true
```

Or use the visual editor (click the pencil icon when editing a card).

### Card Options

| Option | Default | Description |
|--------|---------|-------------|
| `header` | `"Requestarr"` | Card title shown in the header |
| `show_radarr` | `true` | Show Movies tab (only if Radarr is configured) |
| `show_sonarr` | `true` | Show TV tab (only if Sonarr is configured) |
| `show_lidarr` | `true` | Show Music tab (only if Lidarr is configured) |

## Sensors

The integration creates library count sensors for each configured service:

- `sensor.requestarr_radarr` — Total movies in Radarr
- `sensor.requestarr_sonarr` — Total TV series in Sonarr
- `sensor.requestarr_lidarr` — Total artists in Lidarr

Sensors update every 5 minutes. The `library_count` attribute matches the sensor state.

## Links

- [Documentation](https://github.com/Dabentz/ha-requestarr)
- [Issues](https://github.com/Dabentz/ha-requestarr/issues)

## License

MIT
