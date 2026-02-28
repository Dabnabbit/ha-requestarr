/**
 * Requestarr Card
 *
 * Lovelace card for searching and requesting movies/TV via Radarr and Sonarr.
 * Phase 4 will activate the Music tab (Lidarr).
 */

const LitElement = customElements.get("hui-masonry-view")
  ? Object.getPrototypeOf(customElements.get("hui-masonry-view"))
  : Object.getPrototypeOf(customElements.get("hui-view"));
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;

const CARD_VERSION = "0.3.0";

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
      _query: { type: String },
      _results: { type: Array },
      _loading: { type: Boolean },
      _dialogItem: { type: Object },
      _requesting: { type: Object },
      _requestError: { type: Object },
    };
  }

  constructor() {
    super();
    this._activeTab = "movies";
    this._query = "";
    this._results = [];
    this._loading = false;
    this._dialogItem = null;
    this._requesting = {};
    this._requestError = {};
    this._debounceTimer = null;
    this._searchSeq = 0;
  }

  static getConfigElement() {
    return document.createElement("requestarr-card-editor");
  }

  static getStubConfig() {
    return { header: "Requestarr" };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this.config = { header: "Requestarr", ...config };
  }

  getCardSize() {
    return 3;
  }

  getGridOptions() {
    return {
      rows: 3,
      columns: 6,
      min_rows: 2,
      min_columns: 3,
    };
  }

  // ---------------------------------------------------------------------------
  // Event handlers
  // ---------------------------------------------------------------------------

  _onSearchInput(e) {
    this._query = e.target.value;
    clearTimeout(this._debounceTimer);
    if (this._query.length < 2) {
      this._results = [];
      return;
    }
    this._debounceTimer = setTimeout(() => this._doSearch(), 300);
  }

  _switchTab(tab) {
    if (this._activeTab === tab) return;
    this._activeTab = tab;
    this._results = [];
    if (this._query.length >= 2) {
      clearTimeout(this._debounceTimer);
      this._doSearch();
    }
  }

  // ---------------------------------------------------------------------------
  // Search
  // ---------------------------------------------------------------------------

  async _doSearch() {
    const type =
      this._activeTab === "movies"
        ? "requestarr/search_movies"
        : "requestarr/search_tv";
    const seq = ++this._searchSeq;
    this._loading = true;
    try {
      const resp = await this.hass.connection.sendMessagePromise({
        type,
        query: this._query,
      });
      if (seq !== this._searchSeq) return;
      this._results = resp.results || [];
    } catch (_err) {
      if (seq !== this._searchSeq) return;
      this._results = [];
    } finally {
      if (seq === this._searchSeq) this._loading = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Request
  // ---------------------------------------------------------------------------

  _getItemState(item) {
    const key = String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
    const reqState = this._requesting[key];
    if (reqState === "requested") return "requested";
    if (!item.in_library) return "not_in_library";
    if (item.has_file) return "available";
    return "monitored";
  }

  async _doRequest(item) {
    const key = String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
    this._requesting = { ...this._requesting, [key]: "requesting" };
    this._dialogItem = null;

    const isMovie = this._activeTab === "movies";
    const payload = isMovie
      ? {
          type: "requestarr/request_movie",
          tmdb_id: item.tmdb_id,
          title: item.title,
          title_slug: item.title_slug,
        }
      : {
          type: "requestarr/request_series",
          tvdb_id: item.tvdb_id,
          title: item.title,
          title_slug: item.title_slug,
          seasons: item.seasons || [],
        };

    try {
      const resp = await this.hass.connection.sendMessagePromise(payload);
      if (resp.success) {
        this._requesting = { ...this._requesting, [key]: "requested" };
      } else {
        this._requesting = { ...this._requesting, [key]: "error" };
        this._requestError = {
          ...this._requestError,
          [key]: resp.message || "Request failed",
        };
      }
    } catch (_err) {
      this._requesting = { ...this._requesting, [key]: "error" };
      this._requestError = {
        ...this._requestError,
        [key]: "Connection error",
      };
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  render() {
    if (!this.hass || !this.config) {
      return html`<ha-card
        ><div class="loading">
          <ha-spinner size="small"></ha-spinner>
        </div></ha-card
      >`;
    }
    return html`
      <ha-card header="${this.config.header || ""}">
        <div class="card-content">
          ${this._renderTabs()} ${this._renderSearch()} ${this._renderResults()}
        </div>
        ${this._renderDialog()}
      </ha-card>
    `;
  }

  _renderTabs() {
    return html`
      <div class="tabs">
        <button
          class="tab ${this._activeTab === "movies" ? "active" : ""}"
          @click="${() => this._switchTab("movies")}"
        >
          Movies
        </button>
        <button
          class="tab ${this._activeTab === "tv" ? "active" : ""}"
          @click="${() => this._switchTab("tv")}"
        >
          TV
        </button>
        <button class="tab disabled" disabled title="Coming in Phase 4">
          Music
        </button>
      </div>
    `;
  }

  _renderSearch() {
    return html`
      <div class="search-wrap">
        <input
          class="search-input"
          type="search"
          placeholder="Search..."
          .value="${this._query}"
          @input="${this._onSearchInput}"
        />
        ${this._loading
          ? html`<ha-spinner
              size="small"
              class="search-spinner"
            ></ha-spinner>`
          : ""}
      </div>
    `;
  }

  _renderResults() {
    if (this._query.length < 2) return html``;
    if (!this._loading && this._results.length === 0) {
      return html`<div class="empty">No results for "${this._query}"</div>`;
    }
    return html`
      <div class="results">
        ${this._results.map((item) => this._renderResultRow(item))}
      </div>
    `;
  }

  _renderResultRow(item) {
    const state = this._getItemState(item);
    const key = String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
    const reqErr = this._requestError[key];
    return html`
      <div class="result-row">
        <div class="poster-wrap">
          ${item.poster_url
            ? html`<img
                class="poster"
                src="${item.poster_url}"
                alt=""
                @error="${(e) => {
                  e.target.style.display = "none";
                }}"
              />`
            : ""}
          <div class="poster-placeholder"></div>
        </div>
        <div class="result-info">
          <span class="result-title">${item.title}</span>
          ${item.year
            ? html`<span class="result-year">${item.year}</span>`
            : ""}
          ${this._renderStatus(state, item)}
          ${reqErr
            ? html`<span class="req-error">${reqErr}</span>`
            : ""}
        </div>
      </div>
    `;
  }

  _renderStatus(state, item) {
    const key = String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
    const isRequesting = this._requesting[key] === "requesting";
    switch (state) {
      case "available":
        return html`<span class="badge badge-available">Available</span>`;
      case "monitored":
        return html`<span class="badge badge-monitored">Monitored</span>`;
      case "requested":
        return html`<span class="badge badge-requested">Requested</span>`;
      case "not_in_library":
      default:
        return html`<button
          class="req-btn"
          ?disabled="${isRequesting}"
          @click="${() => {
            this._dialogItem = item;
          }}"
        >
          ${isRequesting ? "Requesting\u2026" : "Request"}
        </button>`;
    }
  }

  _renderDialog() {
    if (!this._dialogItem) return html``;
    const item = this._dialogItem;
    const key = String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
    const isRequesting = this._requesting[key] === "requesting";
    return html`
      <div
        class="dialog-overlay"
        @click="${() => {
          this._dialogItem = null;
        }}"
      >
        <div
          class="dialog"
          @click="${(e) => e.stopPropagation()}"
        >
          <div class="dialog-title">${item.title}</div>
          <div class="dialog-meta">
            <div>Profile: ${item.quality_profile || "\u2014"}</div>
            <div>Folder: ${item.root_folder || "\u2014"}</div>
          </div>
          <div class="dialog-actions">
            <button
              class="btn-cancel"
              @click="${() => {
                this._dialogItem = null;
              }}"
            >
              Cancel
            </button>
            <button
              class="btn-confirm"
              ?disabled="${isRequesting}"
              @click="${() => this._doRequest(item)}"
            >
              ${isRequesting ? "Requesting\u2026" : "Confirm"}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
      }
      .card-content {
        padding: 0 16px 16px;
      }

      /* Tabs */
      .tabs {
        display: flex;
        gap: 4px;
        padding: 12px 0 8px;
        border-bottom: 1px solid var(--divider-color);
        margin-bottom: 12px;
      }
      .tab {
        background: none;
        border: none;
        padding: 6px 14px;
        border-radius: 16px;
        cursor: pointer;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--secondary-text-color);
        transition: background 0.15s, color 0.15s;
      }
      .tab.active {
        background: var(--primary-color);
        color: white;
      }
      .tab:hover:not(.active):not(.disabled) {
        background: var(--secondary-background-color);
      }
      .tab.disabled {
        opacity: 0.4;
        cursor: default;
      }

      /* Search */
      .search-wrap {
        position: relative;
        margin-bottom: 12px;
      }
      .search-input {
        width: 100%;
        box-sizing: border-box;
        padding: 8px 12px;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
        font-size: 1rem;
        outline: none;
      }
      .search-input:focus {
        border-color: var(--primary-color);
      }
      .search-spinner {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
      }

      /* Results */
      .results {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .empty {
        color: var(--secondary-text-color);
        padding: 16px 0;
        text-align: center;
      }
      .result-row {
        display: flex;
        gap: 12px;
        align-items: flex-start;
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .result-row:last-child {
        border-bottom: none;
      }

      /* Poster */
      .poster-wrap {
        position: relative;
        flex-shrink: 0;
        width: 60px;
        height: 90px;
        border-radius: 4px;
        overflow: hidden;
        background: var(--secondary-background-color);
      }
      .poster {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .poster-placeholder {
        position: absolute;
        inset: 0;
      }

      /* Result info */
      .result-info {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding-top: 2px;
      }
      .result-title {
        font-weight: 500;
        color: var(--primary-text-color);
        font-size: 0.9rem;
        line-height: 1.3;
      }
      .result-year {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
      }
      .req-error {
        color: var(--error-color, #f44336);
        font-size: 0.8rem;
      }

      /* Status badges */
      .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
        align-self: flex-start;
      }
      .badge-available {
        background: var(--success-color, #4caf50);
      }
      .badge-monitored {
        background: var(--info-color, var(--primary-color, #2196f3));
      }
      .badge-requested {
        background: var(--warning-color, #ff9800);
      }

      /* Request button */
      .req-btn {
        padding: 4px 12px;
        border: none;
        border-radius: 6px;
        background: var(--primary-color);
        color: white;
        cursor: pointer;
        font-size: 0.8rem;
        font-weight: 500;
        align-self: flex-start;
      }
      .req-btn:disabled {
        opacity: 0.6;
        cursor: default;
      }
      .req-btn:hover:not(:disabled) {
        filter: brightness(1.1);
      }

      /* Confirm dialog */
      .dialog-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 999;
      }
      .dialog {
        background: var(--card-background-color);
        border-radius: 12px;
        padding: 20px;
        min-width: 280px;
        max-width: 360px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      }
      .dialog-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--primary-text-color);
        margin-bottom: 12px;
      }
      .dialog-meta {
        color: var(--secondary-text-color);
        font-size: 0.85rem;
        margin-bottom: 16px;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .dialog-actions {
        display: flex;
        gap: 8px;
        justify-content: flex-end;
      }
      .btn-cancel {
        padding: 8px 16px;
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        background: none;
        color: var(--primary-text-color);
        cursor: pointer;
      }
      .btn-confirm {
        padding: 8px 16px;
        border: none;
        border-radius: 6px;
        background: var(--primary-color);
        color: white;
        cursor: pointer;
        font-weight: 500;
      }
      .btn-confirm:disabled {
        opacity: 0.6;
        cursor: default;
      }

      /* Loading state (initial card load) */
      .loading {
        display: flex;
        justify-content: center;
        padding: 32px 16px;
      }
    `;
  }
}

/**
 * Card Editor — minimal stub; full editor added in Phase 5.
 */
class RequestarrCardEditor extends LitElement {
  static get properties() {
    return { hass: {}, config: {} };
  }

  setConfig(config) {
    this.config = config;
  }

  render() {
    return html``;
  }
}

if (!customElements.get("requestarr-card")) {
  customElements.define("requestarr-card", RequestarrCard);
}
if (!customElements.get("requestarr-card-editor")) {
  customElements.define("requestarr-card-editor", RequestarrCardEditor);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "requestarr-card",
  name: "Requestarr Card",
  description: "HA-native media request dashboard for Radarr, Sonarr, and Lidarr.",
  preview: true,
});
