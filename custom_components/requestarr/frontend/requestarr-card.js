/**
 * Requestarr Card
 *
 * A Lovelace card for searching and requesting media
 * from TMDB via Radarr, Sonarr, and Lidarr.
 */

const LitElement = customElements.get("hui-masonry-view")
  ? Object.getPrototypeOf(customElements.get("hui-masonry-view"))
  : Object.getPrototypeOf(customElements.get("hui-view"));
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;

const CARD_VERSION = "0.1.0";

console.info(
  `%c REQUESTARR-CARD %c v${CARD_VERSION} `,
  "color: orange; font-weight: bold; background: black",
  "color: white; font-weight: bold; background: dimgray"
);

class RequestarrCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
      _activeTab: { type: String },
      _searchQuery: { type: String },
      _searchResults: { type: Array },
      _searching: { type: Boolean },
    };
  }

  constructor() {
    super();
    this._activeTab = "movies";
    this._searchQuery = "";
    this._searchResults = [];
    this._searching = false;
  }

  static getConfigElement() {
    return document.createElement("requestarr-card-editor");
  }

  static getStubConfig() {
    return {
      header: "Media Requests",
    };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this.config = { header: "Media Requests", ...config };
  }

  getCardSize() {
    return 5;
  }

  render() {
    if (!this.hass || !this.config) return html``;

    return html`
      <ha-card header="${this.config.header}">
        <div class="card-content">
          <div class="tabs">
            <button
              class="${this._activeTab === "movies" ? "active" : ""}"
              @click="${() => this._setTab("movies")}"
            >
              Movies
            </button>
            <button
              class="${this._activeTab === "tv" ? "active" : ""}"
              @click="${() => this._setTab("tv")}"
            >
              TV Shows
            </button>
            <button
              class="${this._activeTab === "music" ? "active" : ""}"
              @click="${() => this._setTab("music")}"
            >
              Music
            </button>
          </div>

          <div class="search-bar">
            <input
              type="text"
              placeholder="Search ${this._activeTab}..."
              .value="${this._searchQuery}"
              @input="${this._onSearchInput}"
              @keydown="${this._onSearchKeydown}"
            />
            <button class="search-btn" @click="${this._doSearch}">
              ${this._searching ? "..." : "Search"}
            </button>
          </div>

          <div class="results">
            ${this._searchResults.length === 0
              ? html`<div class="empty">
                  Search for ${this._activeTab} to request
                </div>`
              : this._searchResults.map(
                  (item) => html`
                    <div class="result-item">
                      <div class="result-poster">
                        ${item.poster_path
                          ? html`<img
                              src="https://image.tmdb.org/t/p/w92${item.poster_path}"
                              alt="${item.title || item.name}"
                            />`
                          : html`<div class="no-poster">?</div>`}
                      </div>
                      <div class="result-info">
                        <div class="result-title">
                          ${item.title || item.name}
                        </div>
                        <div class="result-year">
                          ${(item.release_date || item.first_air_date || "").substring(0, 4)}
                        </div>
                        <div class="result-overview">
                          ${(item.overview || "").substring(0, 100)}${(item.overview || "").length > 100 ? "..." : ""}
                        </div>
                      </div>
                      <button
                        class="request-btn"
                        @click="${() => this._requestItem(item)}"
                      >
                        Request
                      </button>
                    </div>
                  `
                )}
          </div>

          <div class="stats">
            ${this._renderStats()}
          </div>
        </div>
      </ha-card>
    `;
  }

  _renderStats() {
    const sensors = ["radarr_movies", "sonarr_series", "lidarr_artists"];
    const icons = {
      radarr_movies: "mdi:movie-outline",
      sonarr_series: "mdi:television-classic",
      lidarr_artists: "mdi:music",
    };
    const labels = {
      radarr_movies: "Movies",
      sonarr_series: "Series",
      lidarr_artists: "Artists",
    };

    return html`
      <div class="stats-row">
        ${sensors.map((s) => {
          const entityId = `sensor.requestarr_${s}`;
          const state = this.hass.states[entityId];
          if (!state || state.state === "unavailable") return html``;
          return html`
            <div class="stat">
              <ha-icon icon="${icons[s]}"></ha-icon>
              <span class="stat-value">${state.state}</span>
              <span class="stat-label">${labels[s]}</span>
            </div>
          `;
        })}
      </div>
    `;
  }

  _setTab(tab) {
    this._activeTab = tab;
    this._searchResults = [];
    this._searchQuery = "";
  }

  _onSearchInput(ev) {
    this._searchQuery = ev.target.value;
  }

  _onSearchKeydown(ev) {
    if (ev.key === "Enter") this._doSearch();
  }

  async _doSearch() {
    if (!this._searchQuery.trim()) return;
    this._searching = true;

    // Call HA service to search via the coordinator
    // For now, use TMDB directly from the card as a fallback
    const mediaType =
      this._activeTab === "movies"
        ? "movie"
        : this._activeTab === "tv"
          ? "tv"
          : "multi";

    try {
      // TODO: Call via hass.callWS or a custom service
      // For scaffold purposes, show placeholder behavior
      this._searchResults = [];
    } finally {
      this._searching = false;
    }
  }

  _requestItem(item) {
    // TODO: Call hass service to send request to Radarr/Sonarr/Lidarr
    const event = new CustomEvent("hass-notification", {
      detail: { message: `Requested: ${item.title || item.name}` },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }

  static get styles() {
    return css`
      ha-card {
        padding: 16px;
      }
      .card-content {
        padding: 0 16px 16px;
      }
      .tabs {
        display: flex;
        gap: 4px;
        margin-bottom: 16px;
        border-bottom: 2px solid var(--divider-color, #e0e0e0);
        padding-bottom: 4px;
      }
      .tabs button {
        flex: 1;
        padding: 8px 16px;
        border: none;
        background: transparent;
        color: var(--secondary-text-color);
        font-size: 14px;
        cursor: pointer;
        border-radius: 4px 4px 0 0;
        transition: all 0.2s;
      }
      .tabs button.active {
        color: var(--primary-color);
        background: var(--primary-color-light, rgba(var(--rgb-primary-color), 0.1));
        font-weight: 600;
      }
      .tabs button:hover {
        background: var(--secondary-background-color);
      }
      .search-bar {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
      }
      .search-bar input {
        flex: 1;
        padding: 8px 12px;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 4px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 14px;
      }
      .search-bar input:focus {
        outline: none;
        border-color: var(--primary-color);
      }
      .search-btn {
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
        background: var(--primary-color);
        color: var(--text-primary-color, white);
        cursor: pointer;
        font-size: 14px;
      }
      .results {
        max-height: 400px;
        overflow-y: auto;
      }
      .result-item {
        display: flex;
        gap: 12px;
        padding: 12px 0;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        align-items: flex-start;
      }
      .result-poster img {
        width: 60px;
        border-radius: 4px;
      }
      .no-poster {
        width: 60px;
        height: 90px;
        background: var(--secondary-background-color);
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--secondary-text-color);
        font-size: 24px;
      }
      .result-info {
        flex: 1;
        min-width: 0;
      }
      .result-title {
        font-weight: 600;
        color: var(--primary-text-color);
      }
      .result-year {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .result-overview {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-top: 4px;
        line-height: 1.3;
      }
      .request-btn {
        padding: 6px 12px;
        border: none;
        border-radius: 4px;
        background: var(--primary-color);
        color: var(--text-primary-color, white);
        cursor: pointer;
        font-size: 12px;
        white-space: nowrap;
        align-self: center;
      }
      .empty {
        color: var(--secondary-text-color);
        font-style: italic;
        text-align: center;
        padding: 32px 16px;
      }
      .stats-row {
        display: flex;
        justify-content: space-around;
        padding-top: 16px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
        margin-top: 16px;
      }
      .stat {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
      }
      .stat ha-icon {
        color: var(--primary-color);
        --mdc-icon-size: 20px;
      }
      .stat-value {
        font-size: 1.2em;
        font-weight: bold;
        color: var(--primary-text-color);
      }
      .stat-label {
        font-size: 11px;
        color: var(--secondary-text-color);
      }
    `;
  }
}

/**
 * Card Editor
 */
class RequestarrCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
    };
  }

  setConfig(config) {
    this.config = config;
  }

  render() {
    if (!this.hass || !this.config) return html``;

    return html`
      <div class="editor">
        <ha-textfield
          label="Header"
          .value="${this.config.header || ""}"
          @input="${this._headerChanged}"
        ></ha-textfield>
      </div>
    `;
  }

  _headerChanged(ev) {
    this._updateConfig("header", ev.target.value);
  }

  _updateConfig(key, value) {
    if (!this.config) return;
    const newConfig = { ...this.config, [key]: value };
    const event = new CustomEvent("config-changed", {
      detail: { config: newConfig },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }

  static get styles() {
    return css`
      .editor {
        display: flex;
        flex-direction: column;
        gap: 16px;
        padding: 16px;
      }
    `;
  }
}

customElements.define("requestarr-card", RequestarrCard);
customElements.define("requestarr-card-editor", RequestarrCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "requestarr-card",
  name: "Requestarr Card",
  description: "Search and request movies, TV shows, and music",
  preview: true,
});
