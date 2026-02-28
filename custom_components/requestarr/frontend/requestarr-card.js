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

const CARD_VERSION = "0.5.0";

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
    return { header: "Requestarr", show_radarr: true, show_sonarr: true, show_lidarr: true };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this.config = { header: "Requestarr", ...config };
    const tabMap = { movies: "show_radarr", tv: "show_sonarr", music: "show_lidarr" };
    if (this._activeTab && this.config[tabMap[this._activeTab]] === false) {
      this._activeTab = this._firstVisibleTab() || "movies";
    }
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
        : this._activeTab === "tv"
        ? "requestarr/search_tv"
        : "requestarr/search_music";
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
    const key =
      item.foreign_artist_id != null
        ? String(item.foreign_artist_id)
        : String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
    const reqState = this._requesting[key];
    if (reqState === "requested") return "requested";
    if (item.in_library) return "in_library";
    return "not_in_library";
  }

  async _doRequest(item) {
    const key =
      item.foreign_artist_id != null
        ? String(item.foreign_artist_id)
        : String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
    this._requesting = { ...this._requesting, [key]: "requesting" };
    this._dialogItem = null;

    let payload;
    if (this._activeTab === "movies") {
      payload = {
        type: "requestarr/request_movie",
        tmdb_id: item.tmdb_id,
        title: item.title,
        title_slug: item.title_slug,
      };
    } else if (this._activeTab === "tv") {
      payload = {
        type: "requestarr/request_series",
        tvdb_id: item.tvdb_id,
        title: item.title,
        title_slug: item.title_slug,
        seasons: item.seasons || [],
      };
    } else {
      // music
      payload = {
        type: "requestarr/request_artist",
        foreign_artist_id: item.foreign_artist_id,
        title: item.title,
      };
    }

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
  // Music helpers
  // ---------------------------------------------------------------------------

  _hashColor(name) {
    let h = 5381;
    for (let i = 0; i < name.length; i++) {
      h = ((h << 5) + h) ^ name.charCodeAt(i);
      h = h >>> 0;
    }
    const palette = [
      "#E57373", "#F06292", "#BA68C8", "#7986CB",
      "#4FC3F7", "#4DB6AC", "#81C784", "#FFD54F",
      "#FF8A65", "#A1887F",
    ];
    return palette[h % palette.length];
  }

  _renderMusicResultRow(item) {
    const key = String(item.foreign_artist_id);
    const state = this._getItemState(item);
    const reqErr = this._requestError[key];
    const initial = item.title ? item.title[0].toUpperCase() : "?";
    const color = this._hashColor(item.title || "");
    return html`
      <div class="result-row music-result-row">
        <div class="avatar-wrap">
          ${item.poster_url
            ? html`<img
                class="avatar"
                src="${item.poster_url}"
                alt=""
                @error="${(e) => {
                  e.target.style.display = "none";
                }}"
              />`
            : ""}
          <div
            class="avatar-placeholder"
            style="background-color: ${color}"
          >
            ${initial}
          </div>
          ${item.in_library
            ? html`<span class="badge-in-library">In Library</span>`
            : ""}
        </div>
        <div class="result-info">
          <span class="result-title">${item.title}</span>
          ${this._renderStatus(state, key, item)}
          ${reqErr
            ? html`<span class="req-error">${reqErr}</span>`
            : ""}
        </div>
      </div>
    `;
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

  _firstVisibleTab() {
    if (this.config.show_radarr !== false) return "movies";
    if (this.config.show_sonarr !== false) return "tv";
    if (this.config.show_lidarr !== false) return "music";
    return null;
  }

  _renderTabs() {
    const showMovies = this.config.show_radarr !== false;
    const showTV = this.config.show_sonarr !== false;
    const showMusic = this.config.show_lidarr !== false;

    if (!showMovies && !showTV && !showMusic) {
      return html`<div class="tabs"><span class="tab">No services enabled</span></div>`;
    }

    return html`
      <div class="tabs">
        ${showMovies ? html`<button
          class="tab ${this._activeTab === "movies" ? "active" : ""}"
          @click="${() => this._switchTab("movies")}"
        >
          Movies
        </button>` : ""}
        ${showTV ? html`<button
          class="tab ${this._activeTab === "tv" ? "active" : ""}"
          @click="${() => this._switchTab("tv")}"
        >
          TV
        </button>` : ""}
        ${showMusic ? html`<button
          class="tab ${this._activeTab === "music" ? "active" : ""}"
          @click="${() => this._switchTab("music")}"
        >
          Music
        </button>` : ""}
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
        ${this._results.map((item) =>
          this._activeTab === "music"
            ? this._renderMusicResultRow(item)
            : this._renderResultRow(item)
        )}
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
          ${item.in_library
            ? html`<span class="badge-in-library">In Library</span>`
            : ""}
        </div>
        <div class="result-info">
          <span class="result-title">${item.title}</span>
          ${item.year
            ? html`<span class="result-year">${item.year}</span>`
            : ""}
          ${this._renderStatus(state, key, item)}
          ${reqErr
            ? html`<span class="req-error">${reqErr}</span>`
            : ""}
        </div>
      </div>
    `;
  }

  _renderStatus(state, key, item) {
    const isRequesting = this._requesting[key] === "requesting";
    switch (state) {
      case "in_library":
        return html`<button class="req-btn req-btn-in-library" disabled>In Library</button>`;
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
    const key =
      item.foreign_artist_id != null
        ? String(item.foreign_artist_id)
        : String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
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
            ${this._activeTab === "music" && item.metadata_profile
              ? html`<div>Metadata: ${item.metadata_profile}</div>`
              : ""}
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

      /* Music avatar (circular) */
      .music-result-row {
        align-items: center;
      }
      .avatar-wrap {
        position: relative;
        flex-shrink: 0;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        overflow: hidden;
        background: var(--secondary-background-color);
      }
      .avatar {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: 50%;
      }
      .avatar-placeholder {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-size: 1.4rem;
        font-weight: 700;
        color: white;
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

      /* In Library badge overlay on poster/avatar */
      .badge-in-library {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: #4caf50;
        color: white;
        font-size: 0.6rem;
        font-weight: 700;
        text-align: center;
        padding: 2px 0;
        letter-spacing: 0.03em;
      }

      /* Disabled "In Library" button state */
      .req-btn-in-library {
        background: #9e9e9e;
        color: white;
        cursor: default;
      }
      .req-btn-in-library:hover {
        filter: none;
      }
    `;
  }
}

class RequestarrCardEditor extends LitElement {
  static get properties() {
    return { hass: {}, config: {} };
  }

  setConfig(config) {
    this.config = { header: "Requestarr", ...config };
  }

  _isServiceConfigured(service) {
    if (!this.hass) return false;
    return Object.keys(this.hass.states).some((k) =>
      k.startsWith(`sensor.requestarr_${service}`)
    );
  }

  _fireConfigChanged(newConfig) {
    const ev = new Event("config-changed", { bubbles: true, composed: true });
    ev.detail = { config: newConfig };
    this.dispatchEvent(ev);
  }

  _onToggle(ev) {
    const key = ev.target.dataset.configKey;
    const newConfig = { ...this.config, [key]: ev.target.checked };
    this._fireConfigChanged(newConfig);
  }

  _onTitleInput(ev) {
    const newConfig = { ...this.config, header: ev.target.value };
    this._fireConfigChanged(newConfig);
  }

  render() {
    if (!this.config || !this.hass) return html``;
    const services = [
      { id: "radarr", label: "Show Radarr tab", key: "show_radarr" },
      { id: "sonarr", label: "Show Sonarr tab", key: "show_sonarr" },
      { id: "lidarr", label: "Show Lidarr tab", key: "show_lidarr" },
    ];
    const configuredServices = services.filter((s) =>
      this._isServiceConfigured(s.id)
    );
    return html`
      <div class="editor">
        <div class="editor-row">
          <label class="editor-label">Card Title</label>
          <input
            class="editor-input"
            type="text"
            .value="${this.config.header || "Requestarr"}"
            @input="${this._onTitleInput}"
          />
        </div>
        ${configuredServices.map(
          (s) => html`
            <div class="editor-row editor-row-toggle">
              <label>
                <input
                  type="checkbox"
                  data-config-key="${s.key}"
                  .checked="${this.config[s.key] !== false}"
                  @change="${this._onToggle}"
                />
                ${s.label}
              </label>
            </div>
          `
        )}
        ${configuredServices.length === 0
          ? html`<div class="editor-hint">No arr services configured yet. Add the Requestarr integration first.</div>`
          : ""}
      </div>
    `;
  }

  static get styles() {
    return css`
      .editor {
        padding: 8px 0;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .editor-row {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .editor-row-toggle {
        flex-direction: row;
        align-items: center;
      }
      .editor-label {
        font-size: 0.85rem;
        color: var(--secondary-text-color);
        font-weight: 500;
      }
      .editor-input {
        padding: 6px 10px;
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
        font-size: 0.9rem;
      }
      .editor-hint {
        font-size: 0.8rem;
        color: var(--secondary-text-color);
        font-style: italic;
      }
    `;
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
