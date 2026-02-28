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

const CARD_VERSION = "0.6.5";

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
      _expandedRows: { type: Object },
      _albumCache: { type: Object },
      _albumLoading: { type: Object },
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
    this._expandedRows = {};
    this._albumCache = {};
    this._albumLoading = {};
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
      rows: 8,
      columns: 6,
      min_rows: 4,
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
      // Reset expand state for fresh results
      this._expandedRows = {};
      this._albumCache = {};
      this._albumLoading = {};
    } catch (_err) {
      if (seq !== this._searchSeq) return;
      this._results = [];
    } finally {
      if (seq === this._searchSeq) this._loading = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Expand / collapse
  // ---------------------------------------------------------------------------

  _toggleExpand(key) {
    this._expandedRows = { ...this._expandedRows, [key]: !this._expandedRows[key] };
  }

  async _fetchAlbums(item) {
    const id = item.foreign_artist_id;
    if (this._albumCache[id] !== undefined) return; // already fetched
    this._albumLoading = { ...this._albumLoading, [id]: true };
    try {
      const resp = await this.hass.connection.sendMessagePromise({
        type: "requestarr/get_artist_albums",
        foreign_artist_id: id,
        ...(item.arr_id ? { arr_id: item.arr_id } : {}),
      });
      this._albumCache = { ...this._albumCache, [id]: resp.albums || [] };
    } catch (_err) {
      this._albumCache = { ...this._albumCache, [id]: [] };
    } finally {
      this._albumLoading = { ...this._albumLoading, [id]: false };
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
    if (reqState === "in_library" || item.in_library) return "in_library";
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
      // Request All — send every season as monitored: true
      payload = {
        type: "requestarr/request_series",
        tvdb_id: item.tvdb_id,
        title: item.title,
        title_slug: item.title_slug,
        seasons: (item.seasons || []).map((s) => ({ ...s, monitored: true })),
      };
    } else {
      // music — request all (entire artist)
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
      } else if (resp.error_code === "already_exists") {
        // Already in the arr library — flip to in_library state silently
        this._requesting = { ...this._requesting, [key]: "in_library" };
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

  async _doRequestSeason(item, season) {
    const reqKey = `${item.tvdb_id}:s${season.seasonNumber}`;
    this._requesting = { ...this._requesting, [reqKey]: "requesting" };

    // Only this season monitored; all others false
    const seasons = (item.seasons || []).map((s) => ({
      ...s,
      monitored: s.seasonNumber === season.seasonNumber,
    }));

    try {
      const resp = await this.hass.connection.sendMessagePromise({
        type: "requestarr/request_series",
        tvdb_id: item.tvdb_id,
        title: item.title,
        title_slug: item.title_slug,
        seasons,
      });
      if (resp.success) {
        this._requesting = { ...this._requesting, [reqKey]: "requested" };
      } else if (resp.error_code === "already_exists") {
        this._requesting = { ...this._requesting, [reqKey]: "in_library" };
      } else {
        this._requesting = { ...this._requesting, [reqKey]: "error" };
        this._requestError = {
          ...this._requestError,
          [reqKey]: resp.message || "Request failed",
        };
      }
    } catch (_err) {
      this._requesting = { ...this._requesting, [reqKey]: "error" };
      this._requestError = { ...this._requestError, [reqKey]: "Connection error" };
    }
  }

  async _doRequestAlbum(item, album) {
    const reqKey = `${item.foreign_artist_id}:a${album.foreign_album_id}`;
    this._requesting = { ...this._requesting, [reqKey]: "requesting" };

    try {
      const resp = await this.hass.connection.sendMessagePromise({
        type: "requestarr/request_album",
        foreign_artist_id: item.foreign_artist_id,
        foreign_album_id: album.foreign_album_id,
      });
      if (resp.success) {
        this._requesting = { ...this._requesting, [reqKey]: "requested" };
      } else if (resp.error_code === "already_exists") {
        this._requesting = { ...this._requesting, [reqKey]: "in_library" };
      } else {
        this._requesting = { ...this._requesting, [reqKey]: "error" };
        this._requestError = {
          ...this._requestError,
          [reqKey]: resp.message || "Request failed",
        };
      }
    } catch (_err) {
      this._requesting = { ...this._requesting, [reqKey]: "error" };
      this._requestError = { ...this._requestError, [reqKey]: "Connection error" };
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

  // ---------------------------------------------------------------------------
  // Sub-row renderers
  // ---------------------------------------------------------------------------

  _renderSeasonSubRows(item) {
    // item.seasons is already accurate — the TV search handler fetches
    // /series/{arr_id} for in-library results before returning results.
    const seasons = [...(item.seasons || [])].sort((a, b) => a.seasonNumber - b.seasonNumber);
    return html`
      <div class="sub-rows">
        ${seasons.map((s) => {
          const label = s.seasonNumber === 0 ? "Specials" : `Season ${s.seasonNumber}`;
          const reqKey = `${item.tvdb_id}:s${s.seasonNumber}`;
          const reqState = this._requesting[reqKey];
          const isRequesting = reqState === "requesting";
          const isRequested = reqState === "requested";
          const isInLib = reqState === "in_library" || (item.in_library && !!(s.statistics && s.statistics.episodeFileCount > 0));
          const reqErr = this._requestError[reqKey];
          const epCount =
            s.statistics && s.statistics.totalEpisodeCount != null
              ? s.statistics.totalEpisodeCount
              : null;
          return html`
            <div class="sub-row">
              <div class="sub-row-left">
                <span class="sub-row-label">${label}</span>
                ${epCount != null
                  ? html`<span class="sub-row-meta">${epCount} ep${epCount !== 1 ? "s" : ""}</span>`
                  : ""}
              </div>
              <div class="sub-row-actions">
                ${reqErr
                  ? html`<span class="req-error sub-req-error">${reqErr}</span>`
                  : ""}
                ${isInLib
                  ? html`<button class="req-btn req-btn-in-library req-btn-sm" disabled>
                      In Library
                    </button>`
                  : isRequested
                  ? html`<span class="badge badge-requested">Requested</span>`
                  : html`<button
                      class="req-btn req-btn-sm"
                      ?disabled="${isRequesting}"
                      @click="${() => this._doRequestSeason(item, s)}"
                    >
                      ${isRequesting ? "Requesting\u2026" : "Request"}
                    </button>`}
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }

  _renderAlbumSubRows(item) {
    const id = item.foreign_artist_id;
    if (this._albumLoading[id]) {
      return html`
        <div class="sub-rows">
          <div class="sub-row-loading">
            <ha-spinner size="small"></ha-spinner>
          </div>
        </div>
      `;
    }
    const albums = this._albumCache[id];
    if (!albums || albums.length === 0) {
      return html`
        <div class="sub-rows">
          <div class="sub-row-empty">No albums found</div>
        </div>
      `;
    }
    return html`
      <div class="sub-rows">
        ${albums.map((album) => {
          const reqKey = `${id}:a${album.foreign_album_id}`;
          const reqState = this._requesting[reqKey];
          const isRequesting = reqState === "requesting";
          const isRequested = reqState === "requested";
          const isInLib = reqState === "in_library" || album.in_library || album.monitored;
          const reqErr = this._requestError[reqKey];
          return html`
            <div class="sub-row">
              <div class="sub-row-left">
                <span class="sub-row-label">${album.title}</span>
                ${album.year
                  ? html`<span class="sub-row-meta">${album.year}</span>`
                  : ""}
              </div>
              <div class="sub-row-actions">
                ${reqErr
                  ? html`<span class="req-error sub-req-error">${reqErr}</span>`
                  : ""}
                ${isInLib
                  ? html`<button class="req-btn req-btn-in-library req-btn-sm" disabled>
                      In Library
                    </button>`
                  : isRequested
                  ? html`<span class="badge badge-requested">Requested</span>`
                  : html`<button
                      class="req-btn req-btn-sm"
                      ?disabled="${isRequesting}"
                      @click="${() => this._doRequestAlbum(item, album)}"
                    >
                      ${isRequesting ? "Requesting\u2026" : "Request"}
                    </button>`}
              </div>
            </div>
          `;
        })}
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
    const isTV = this._activeTab === "tv";
    const state = this._getItemState(item);
    const key = String(item.tmdb_id != null ? item.tmdb_id : item.tvdb_id);
    const reqErr = this._requestError[key];
    const seasonCount = item.seasons ? item.seasons.length : null;
    const expanded = isTV && !!this._expandedRows[key];

    return html`
      <div class="result-row">
        <div class="result-row-main">
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
            <span class="result-meta">
              ${item.year ? html`<span class="result-year">${item.year}</span>` : ""}
              ${seasonCount ? html`<span class="result-seasons">${seasonCount} season${seasonCount !== 1 ? "s" : ""}</span>` : ""}
            </span>
            ${item.overview
              ? html`<span class="result-overview">${item.overview}</span>`
              : ""}
            <div class="result-actions">
              ${this._renderStatus(state, key, item, isTV ? "Request All" : "Request")}
              ${isTV
                ? html`<button
                    class="expand-btn"
                    @click="${() => this._toggleExpand(key)}"
                    title="${expanded ? "Collapse seasons" : "Expand seasons"}"
                  >
                    <ha-icon icon="${expanded ? "mdi:chevron-down" : "mdi:chevron-right"}"></ha-icon>
                  </button>`
                : ""}
            </div>
            ${reqErr
              ? html`<span class="req-error">${reqErr}</span>`
              : ""}
          </div>
        </div>
        ${expanded ? this._renderSeasonSubRows(item) : ""}
      </div>
    `;
  }

  _renderMusicResultRow(item) {
    const key = String(item.foreign_artist_id);
    const state = this._getItemState(item);
    const reqErr = this._requestError[key];
    const initial = item.title ? item.title[0].toUpperCase() : "?";
    const color = this._hashColor(item.title || "");
    const expanded = !!this._expandedRows[key];

    return html`
      <div class="result-row music-result-row">
        <div class="result-row-main result-row-main-music">
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
            ${item.overview
              ? html`<span class="result-overview">${item.overview}</span>`
              : ""}
            <div class="result-actions">
              ${this._renderStatus(state, key, item, "Request All")}
              ${item.in_library
                ? html`<button
                    class="expand-btn"
                    @click="${() => {
                      const wasExpanded = this._expandedRows[key];
                      this._toggleExpand(key);
                      if (!wasExpanded) this._fetchAlbums(item);
                    }}"
                    title="${expanded ? "Collapse albums" : "Expand albums"}"
                  >
                    <ha-icon icon="${expanded ? "mdi:chevron-down" : "mdi:chevron-right"}"></ha-icon>
                  </button>`
                : ""}
            </div>
            ${reqErr
              ? html`<span class="req-error">${reqErr}</span>`
              : ""}
          </div>
        </div>
        ${expanded ? this._renderAlbumSubRows(item) : ""}
      </div>
    `;
  }

  _renderStatus(state, key, item, label = "Request") {
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
          ${isRequesting ? "Requesting\u2026" : label}
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
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        height: 100%;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      .card-content {
        flex: 1;
        min-height: 0;
        display: flex;
        flex-direction: column;
        padding: 0 16px 16px;
        overflow: hidden;
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
        gap: 0;
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: var(--divider-color) transparent;
      }
      .empty {
        color: var(--secondary-text-color);
        padding: 16px 0;
        text-align: center;
      }

      /* Result row — now a column wrapper */
      .result-row {
        display: flex;
        flex-direction: column;
        padding: 10px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .result-row:last-child {
        border-bottom: none;
      }

      /* Main row — poster + info + optional expand button */
      .result-row-main {
        display: flex;
        gap: 12px;
        align-items: flex-start;
      }
      .result-row-main-music {
        align-items: center;
      }

      /* Action row — request button + expand chevron side by side */
      .result-actions {
        display: flex;
        align-items: center;
        gap: 6px;
      }

      /* Expand button */
      .expand-btn {
        background: none;
        border: none;
        cursor: pointer;
        padding: 2px;
        color: var(--secondary-text-color);
        flex-shrink: 0;
        display: flex;
        align-items: center;
        border-radius: 50%;
        transition: background 0.15s, color 0.15s;
      }
      .expand-btn:hover {
        background: var(--secondary-background-color);
        color: var(--primary-color);
      }
      .expand-btn ha-icon {
        --mdc-icon-size: 20px;
      }

      /* Sub-rows */
      .sub-rows {
        padding: 4px 0 4px 92px; /* indent past poster width (80px) + gap (12px) */
        display: flex;
        flex-direction: column;
        gap: 0;
        border-top: 1px solid var(--divider-color);
        margin-top: 6px;
      }
      .sub-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .sub-row:last-child {
        border-bottom: none;
      }
      .sub-row-left {
        display: flex;
        flex-direction: column;
        gap: 2px;
        min-width: 0;
      }
      .sub-row-label {
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--primary-text-color);
      }
      .sub-row-meta {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
      }
      .sub-row-actions {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
        margin-left: 8px;
      }
      .sub-req-error {
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .sub-row-loading {
        padding: 8px 0;
        display: flex;
        justify-content: flex-start;
      }
      .sub-row-empty {
        padding: 8px 0;
        font-size: 0.8rem;
        color: var(--secondary-text-color);
      }

      /* Poster */
      .poster-wrap {
        position: relative;
        flex-shrink: 0;
        width: 80px;
        height: 120px;
        border-radius: 6px;
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
        min-width: 0;
      }
      .result-title {
        font-weight: 600;
        color: var(--primary-text-color);
        font-size: 0.95rem;
        line-height: 1.3;
      }
      .result-meta {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .result-year {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
      }
      .result-seasons {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
      }
      .result-overview {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
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
      }
      .req-btn-sm {
        padding: 3px 10px;
        font-size: 0.75rem;
        align-self: auto;
      }
      .req-btn:disabled {
        opacity: 0.6;
        cursor: default;
      }
      .req-btn:hover:not(:disabled) {
        filter: brightness(1.1);
      }

      /* Music avatar (circular) */
      .avatar-wrap {
        position: relative;
        flex-shrink: 0;
        width: 72px;
        height: 72px;
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
