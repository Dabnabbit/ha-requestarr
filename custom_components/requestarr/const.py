"""Constants for the Requestarr integration."""

DOMAIN = "requestarr"

# Config keys
CONF_TMDB_API_KEY = "tmdb_api_key"
CONF_RADARR_URL = "radarr_url"
CONF_RADARR_API_KEY = "radarr_api_key"
CONF_SONARR_URL = "sonarr_url"
CONF_SONARR_API_KEY = "sonarr_api_key"
CONF_LIDARR_URL = "lidarr_url"
CONF_LIDARR_API_KEY = "lidarr_api_key"

# Defaults
DEFAULT_RADARR_PORT = 7878
DEFAULT_SONARR_PORT = 8989
DEFAULT_LIDARR_PORT = 8686
DEFAULT_SCAN_INTERVAL = 300

# API
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"

FRONTEND_SCRIPT_URL = f"/hacsfiles/{DOMAIN}/{DOMAIN}-card.js"
