# Requestarr

HA-native media request dashboard for Radarr, Sonarr, and Lidarr.

[![HACS Default](https://img.shields.io/badge/HACS-Default-blue.svg)](https://github.com/hacs/integration)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2025.7%2B-blue.svg)](https://www.home-assistant.io/)

## Installation via HACS

1. Open HACS in Home Assistant
2. Go to Integrations
3. Search for "Requestarr"
4. Install and restart Home Assistant

## Manual Installation

1. Copy `custom_components/requestarr/` into your HA `config/custom_components/`
2. Restart Home Assistant
3. Add the integration via Settings > Devices & Services > Add Integration

## Card Usage

Add the Lovelace card to your dashboard:

```yaml
type: custom:requestarr-card
entity: sensor.example
header: "Requestarr"
```

## Configuration

Configure the integration via Settings > Devices & Services > Add Integration > Requestarr.

## Links

- [Documentation](https://github.com/Dabentz/ha-requestarr)
- [Issues](https://github.com/Dabentz/ha-requestarr/issues)

## License

MIT
