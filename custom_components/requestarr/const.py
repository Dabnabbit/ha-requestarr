"""Constants for the Requestarr integration."""

DOMAIN = "requestarr"

# Timeouts
DEFAULT_TIMEOUT = 10  # 10-second connection timeout per arr API call
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes in seconds

# Arr service types
SERVICE_RADARR = "radarr"
SERVICE_SONARR = "sonarr"
SERVICE_LIDARR = "lidarr"
ARR_SERVICES = [SERVICE_RADARR, SERVICE_SONARR, SERVICE_LIDARR]

# API versions per service
API_VERSIONS: dict[str, str] = {
    SERVICE_RADARR: "v3",
    SERVICE_SONARR: "v3",
    SERVICE_LIDARR: "v1",
}

# Library count endpoints per service
LIBRARY_ENDPOINTS: dict[str, str] = {
    SERVICE_RADARR: "/movie",
    SERVICE_SONARR: "/series",
    SERVICE_LIDARR: "/artist",
}

# Config keys — Radarr
CONF_RADARR_URL = "radarr_url"
CONF_RADARR_API_KEY = "radarr_api_key"
CONF_RADARR_VERIFY_SSL = "radarr_verify_ssl"
CONF_RADARR_QUALITY_PROFILE_ID = "radarr_quality_profile_id"
CONF_RADARR_ROOT_FOLDER = "radarr_root_folder"
CONF_RADARR_PROFILES = "radarr_profiles"
CONF_RADARR_FOLDERS = "radarr_folders"

# Config keys — Sonarr
CONF_SONARR_URL = "sonarr_url"
CONF_SONARR_API_KEY = "sonarr_api_key"
CONF_SONARR_VERIFY_SSL = "sonarr_verify_ssl"
CONF_SONARR_QUALITY_PROFILE_ID = "sonarr_quality_profile_id"
CONF_SONARR_ROOT_FOLDER = "sonarr_root_folder"
CONF_SONARR_PROFILES = "sonarr_profiles"
CONF_SONARR_FOLDERS = "sonarr_folders"

# Config keys — Lidarr
CONF_LIDARR_URL = "lidarr_url"
CONF_LIDARR_API_KEY = "lidarr_api_key"
CONF_LIDARR_VERIFY_SSL = "lidarr_verify_ssl"
CONF_LIDARR_QUALITY_PROFILE_ID = "lidarr_quality_profile_id"
CONF_LIDARR_ROOT_FOLDER = "lidarr_root_folder"
CONF_LIDARR_METADATA_PROFILE_ID = "lidarr_metadata_profile_id"
CONF_LIDARR_PROFILES = "lidarr_profiles"
CONF_LIDARR_FOLDERS = "lidarr_folders"
CONF_LIDARR_METADATA_PROFILES = "lidarr_metadata_profiles"

# Lookup (search) endpoints per service
LOOKUP_ENDPOINTS: dict[str, str] = {
    SERVICE_RADARR: "/movie/lookup",
    SERVICE_SONARR: "/series/lookup",
    SERVICE_LIDARR: "/artist/lookup",
}

# WebSocket command types — search
WS_TYPE_SEARCH_MOVIES = f"{DOMAIN}/search_movies"
WS_TYPE_SEARCH_TV = f"{DOMAIN}/search_tv"
WS_TYPE_SEARCH_MUSIC = f"{DOMAIN}/search_music"

# WebSocket command types — request
WS_TYPE_REQUEST_MOVIE = f"{DOMAIN}/request_movie"
WS_TYPE_REQUEST_TV = f"{DOMAIN}/request_series"
WS_TYPE_REQUEST_ARTIST = f"{DOMAIN}/request_artist"
WS_TYPE_GET_ARTIST_ALBUMS = f"{DOMAIN}/get_artist_albums"
WS_TYPE_REQUEST_ALBUM = f"{DOMAIN}/request_album"

# Search limits
MAX_SEARCH_RESULTS = 20

# Frontend
FRONTEND_SCRIPT_URL = f"/{DOMAIN}/{DOMAIN}-card.js"
