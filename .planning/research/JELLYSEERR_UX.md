# Jellyseerr UX Analysis for Requestarr Design

**Research Date:** 2026-02-23
**Sources:** Jellyseerr/Seerr GitHub repository source code analysis, Seerr documentation, community discussions, blog reviews

---

## Table of Contents

1. [Search Flow UX](#1-search-flow-ux)
2. [Search Results Display](#2-search-results-display)
3. [Request Flow](#3-request-flow)
4. [Request States & Visual Indicators](#4-request-states--visual-indicators)
5. [Navigation & Layout](#5-navigation--layout)
6. [Media Detail View](#6-media-detail-view)
7. [Mobile/Responsive Design](#7-mobileresponsive-design)
8. [Status Tracking](#8-status-tracking)
9. [Visual Design Language](#9-visual-design-language)
10. [Key UX Patterns Worth Adopting or Avoiding](#10-key-ux-patterns-worth-adopting-or-avoiding)

---

## 1. Search Flow UX

### Search Bar Behavior

**Location:** The search input is embedded in the fixed top header bar (height: `4rem` / 64px), always visible regardless of current page. It is part of the main `Layout` component, not a per-page feature.

**Input Styling:**
- Rounded-full (pill shape) with `border border-gray-600 bg-gray-900`
- Hover: border lightens, background opacity shifts
- Focus: border and background adjust for active state
- Hidden screen-reader label: "Search for movies or TV shows"
- Dynamic right-padding when text is present (accommodates clear button)

**Debounce:** 300ms via custom `useDebouncedState` hook. The input updates local state immediately (responsive typing feel), but the debounced value that triggers API calls and URL changes fires after 300ms of no typing.

**Search-as-you-type with URL routing:**
1. User types in the search bar
2. `searchValue` updates immediately (responsive UI)
3. After 300ms debounce, `debouncedValue` updates
4. A `useEffect` triggers on `debouncedValue` change
5. If not already on `/search`, router navigates to `/search`
6. URL updates to `/search?query=<value>` (uses `router.replace` to avoid polluting history)
7. The Search page component reads `router.query.query` and calls `/api/v1/search`

**Clear button:** An `XCircleIcon` appears when `searchValue.length > 0`, clicking it resets the field via `clear()`.

**Keyboard handling:** Enter key blurs the input (closing any mobile keyboard). No submit button - search is entirely search-as-you-type.

**Navigation on open/close:**
- Opening search: navigates to `/search` route
- Closing search (empty field on blur): returns to previous route (`lastRoute`) or `/` if no history
- This creates a "search mode" UX pattern

**No autocomplete/suggestions dropdown.** Search goes directly to a full results page. There is no typeahead or suggestion list.

### Key Takeaway for Requestarr
The search bar is always available, uses 300ms debounce, and navigates to a results page. For a Lovelace card, we would want an inline search experience rather than page navigation. The 300ms debounce is a good standard to adopt.

---

## 2. Search Results Display

### Grid Layout

**CSS Grid definition:**
```css
/* .cards-vertical class */
grid-template-columns: repeat(auto-fill, minmax(9.375rem, 1fr));
gap: 1rem;
```
This creates a responsive grid where each column is at least **150px** (9.375rem) wide, filling the available space. Gap between cards is **16px**.

### Card Dimensions (TitleCard)

**Width (responsive):**
- Base/Small: `w-36` = **144px**
- Medium+: `w-44` = **176px**
- Can expand to full width with `canExpand` prop

**Aspect ratio:** 150% padding-bottom creates a **2:3 portrait ratio** (standard movie poster proportions).

### Information Per Result Card

**Always visible:**
- **Poster image** from TMDB (fallback placeholder if unavailable)
- **Media type badge** in top-left corner: "Movie", "TV Show", or "Collection"
- **Title** (clamped to 3 lines max via CSS)
- **Year** (4-digit release year)

**On hover (desktop) / tap (mobile):**
- **Description/summary** (5 lines max, or 3 if request button visible)
- **Watchlist toggle** (star icon to add, minus icon if already on watchlist)
- **Hide/Blocklist button** (eye-slash icon, permission-gated)
- **Request button** (conditionally hidden if already available/processing/pending)
- **Status badge** showing current availability state

**Scale effect:** Card scales to 105% with enhanced shadow when detail view activates. Reverts to 100% at rest.

### Pagination

**Infinite scroll:** Uses `useVerticalScroll` hook that calls `fetchMore()` when the user scrolls to the bottom. No pagination controls, no "Load More" button.

**Loading state:** 20 placeholder/skeleton cards rendered while data loads.

**Empty state:** Centered message when no results match the search query.

### Result Types

The ListView handles mixed result types from TMDB:
- **Movies** and **TV shows** render as `TitleCard`
- **People** render as `PersonCard` with profile info
- **Collections** render as simplified `TitleCard`

### Key Takeaway for Requestarr
A Lovelace card cannot do infinite scroll well. Consider a compact list (5-8 results) or a paginated approach. The 2:3 poster ratio and minimal info (poster + title + year + status badge) is the right density for a card. Hover-to-expand works poorly on mobile - need a tap-to-detail pattern instead.

---

## 3. Request Flow

### Click Path: Search to Submitted Request

**Movie request (minimum clicks):**
1. Type query in search bar (search-as-you-type, no submit click needed)
2. Click on movie card in results (navigates to detail page)
3. Click "Request" button on detail page (opens modal)
4. Click "Request" in modal to confirm

**Total: 3 interactions** (type + click result + confirm request). The modal is a confirmation step, not a complex form for regular users.

**TV show request (minimum clicks):**
1. Type query
2. Click on TV show card
3. Click "Request" button
4. Select seasons (checkboxes, "Select All" available in header)
5. Click "Request" to confirm

**Total: 4-5 interactions** depending on season selection.

### Movie Request Modal

**Layout:**
- Backdrop image at top of modal with gradient fade
- Title and subtitle
- Auto-approval alert (if user has auto-approve permission)
- Quota display (remaining movie requests out of limit)
- Advanced requester section (permission-gated, collapsed by default)
- Action buttons at bottom (Request + Cancel)

**Advanced options (shown only with `REQUEST_ADVANCED` permission):**
- Server selection (dropdown - which Radarr instance)
- Quality profile (dropdown - e.g., "HD-1080p", "Ultra-HD")
- Root folder (dropdown - destination path)
- Tags (multi-select)
- User override (admin only - request on behalf of another user)

**For regular household users:** They see only the backdrop, title, optional quota info, and the Request/Cancel buttons. Very simple.

### TV Show Request Modal

**Layout:** Similar to movie but with a season selection table:

| Column | Content |
|--------|---------|
| Checkbox | Select/deselect season |
| Season | Season name/number |
| Episodes | Episode count |
| Status | Badge: not requested / pending / approved / available |

- "Select All" checkbox in table header
- Seasons are filtered (already available or requested seasons may be hidden/disabled)
- No episode-level granularity - selection is per-season only
- Special episodes can be toggled via settings

### Request Submission

**API call:** `POST /api/v1/request` with:
- `mediaId` (TMDB ID)
- `mediaType` ("movie" or "tv")
- `seasons` (array of season numbers, TV only)
- `is4k` (boolean)
- Optional overrides: `serverId`, `profileId`, `rootFolder`, `tags`

**Post-submission:**
- Cache invalidation (SWR mutate)
- `onComplete()` callback fires with new status
- Status becomes `PROCESSING` (if auto-approved) or `PENDING` (if needs approval)
- Modal closes, detail page updates to show new status

### Key Takeaway for Requestarr
For a household of 3-4 people, the advanced requester options (server, quality profile, root folder, tags) are unnecessary complexity. The ideal flow for Requestarr should be: search -> tap result -> one-tap request with automatic defaults. For TV shows, season selection adds unavoidable complexity, but a "Request All" default would cover most cases.

---

## 4. Request States & Visual Indicators

### Status Types and Their Visual Representation

| Status | Badge Color | Label | Icon/Extra |
|--------|------------|-------|-----------|
| **AVAILABLE** | Green (`bg-green-500`) | "Available" | Optional spinner if in-progress; links to Plex/Emby/Jellyfin |
| **PARTIALLY_AVAILABLE** | Green | "Partially Available" | Same as available |
| **PROCESSING** | Indigo/Blue (`bg-indigo-500`) | "Requested" or "Processing" | Animated spinner; green progress bar overlay showing download % |
| **PENDING** | Yellow (`bg-yellow-500`) | "Pending" | Awaiting admin approval |
| **BLOCKLISTED** | Red (`bg-red-600`) | "Blocklisted" | Failed/unavailable content |
| **DELETED** | Red (`bg-red-600`) | "Deleted" or "Processing" | Red progress bar during re-download |

### Badge Component Styling

All status badges share:
- `px-2 inline-flex text-xs leading-5 font-semibold rounded-full whitespace-nowrap`
- Semi-transparent backgrounds (`bg-opacity-80`) with matching border colors
- Hover effects when clickable (darker opacity)

### Color Definitions

```
Success (Available):  bg-green-500, border-green-500, text-green-100
Primary (Processing): bg-indigo-500, border-indigo-500, text-indigo-100
Warning (Pending):    bg-yellow-500, border-yellow-500, text-yellow-100
Danger (Error/Block): bg-red-600, border-red-500, text-red-100
```

### 4K Variants

When 4K is enabled, statuses display with "4K" prefix (e.g., "4K Available", "4K Requested"). Standard and 4K statuses are tracked independently and both can appear simultaneously on the same title.

### Download Progress

For `PROCESSING` status, a colored background bar overlays the badge showing download completion percentage:
- Standard downloads: green progress bar
- Deleted/re-downloading: red progress bar
- TV shows additionally display season/episode info (e.g., "S1E5")

### Where Indicators Appear

1. **On TitleCard (search results / discover page):** Status badge appears on hover/expand
2. **On detail page:** Status badges appear next to title in the header area, both standard and 4K
3. **On request list:** Full status badge with progress, plus action buttons
4. **On request cards:** Color-coded status badges with requester info

### Key Takeaway for Requestarr
The color scheme is solid and well-understood: green = have it, blue/indigo = getting it, yellow = waiting for approval, red = problem. For a household card, the critical statuses to show are: available (green), requested/downloading (blue with progress), and pending (yellow). Blocklist/deleted are edge cases. The badge-based approach with pill shapes works well at small sizes.

---

## 5. Navigation & Layout

### Desktop Layout (>= 1024px / `lg` breakpoint)

```
+------------------+------------------------------------------+
| Sidebar (256px)  | Fixed Header (search bar + user dropdown) |
|                  +------------------------------------------+
| - Discover       |                                          |
| - Movies         |         Main Content Area                |
| - Series         |         (with top-16 offset for header)  |
| - Requests [n]   |                                          |
| - Blocklist      |                                          |
| - Issues [n]     |                                          |
| - Users          |                                          |
| - Settings       |                                          |
+------------------+------------------------------------------+
```

**Sidebar:** Fixed left sidebar at `w-64` (256px). Content area has `lg:ml-64` to offset.

**Sidebar items (in order):**
1. Discover (SparklesIcon) - Route: `/`
2. Movies (FilmIcon) - Route: `/discover/movies`
3. Series (TvIcon) - Route: `/discover/tv`
4. Requests (ClockIcon) - Route: `/requests` - shows pending count badge
5. Blocklist (EyeSlashIcon) - Route: `/blocklist`
6. Issues (ExclamationTriangleIcon) - Route: `/issues`
7. Users (UsersIcon) - Route: `/users`
8. Settings (CogIcon) - Route: `/settings`

Items 5-8 are permission-gated (admin/manage permissions).

**Active state:** Gradient highlight `from-indigo-600 to-purple-600`.

**Header:** Fixed top bar with:
- Sidebar toggle (hidden on lg+)
- Back button (PWA only)
- Search input (pill-shaped, centered)
- User dropdown (right side)
- Background: `bg-gray-700` when scrolled, with backdrop blur

### Mobile Layout (< 1024px)

**Header:** Same fixed top bar, but sidebar toggle visible.

**Sidebar:** Slides in as overlay when toggle clicked.

**Bottom navigation bar (MobileMenu):** Fixed to bottom of screen with 4-5 items from the same navigation list. If more than 5 items are available, an ellipsis button reveals a full overlay menu.

- Items show outline icons when inactive, filled icons when active
- Active state: indigo highlighting
- Badge indicators for pending requests and open issues
- Touch-friendly spacing

### Key Pages

| Page | Purpose | URL |
|------|---------|-----|
| Discover | Trending/popular media sliders | `/` |
| Movies Browse | Movie-specific discovery | `/discover/movies` |
| Series Browse | TV-specific discovery | `/discover/tv` |
| Search Results | Search query results | `/search?query=...` |
| Movie Detail | Full movie info + request | `/movie/{tmdbId}` |
| TV Detail | Full show info + request | `/tv/{tmdbId}` |
| Requests | Request list with filters | `/requests` |
| Profile | User dashboard + recent requests | `/profile` |
| Settings | Admin configuration | `/settings` |

### Discover Page Structure

The discover page is a vertical stack of horizontal media sliders:
- Trending content (from TMDB)
- Popular movies and TV shows
- Upcoming releases
- Genre sliders (with color-coded genre cards)
- Custom admin-configured sliders (keywords, studios, networks, streaming services)
- Plex Watchlist integration
- Recently added and requested media

Each slider is a horizontal scrollable container with left/right chevron navigation buttons. Uses `react-spring` for smooth scroll animation (friction: 60, tension: 500, velocity: 20).

### Key Takeaway for Requestarr
A Lovelace card does not need navigation - it is a single-purpose widget. The key insight is that Jellyseerr has essentially 3 core user flows: (1) discover/browse, (2) search + request, and (3) track my requests. Requestarr should focus on flow #2 (search + request) as the primary interaction, with #3 (request status) as secondary information always visible. Flow #1 (discover) is nice-to-have but adds significant complexity.

---

## 6. Media Detail View

### Movie Detail Page Layout

```
+------------------------------------------------------------------+
| [Backdrop Image - full width, gradient overlay to gray-900]      |
|                                                                   |
|  [Poster]  Title (Year)                    [Action Buttons Row]  |
|  150x225   [Status Badges]                  - Blocklist          |
|            Certification | Runtime | Genres  - Watchlist star    |
|                                              - Play button       |
|                                              - Request button    |
|                                              - Report issue      |
|                                              - Manage            |
+------------------------------------------------------------------+
| LEFT COLUMN (wider)          | RIGHT COLUMN (narrower)           |
|                              |                                    |
| Tagline (italic)             | [Collection Card] (if applicable) |
| Overview text                | Ratings:                          |
| Top 6 crew members           |   - Rotten Tomatoes              |
| Keywords (tag links)         |   - IMDB                         |
|                              |   - TMDB                         |
|                              | Facts Panel:                     |
|                              |   - Original Title               |
|                              |   - Status                       |
|                              |   - Release Dates                |
|                              |   - Revenue / Budget             |
|                              |   - Language                     |
|                              |   - Production Countries         |
|                              |   - Studios                      |
|                              | Streaming Providers (logos)      |
+------------------------------+------------------------------------+
| Cast Slider (top 20 cast, horizontal scroll)                     |
+------------------------------------------------------------------+
| Recommendations Slider (horizontal scroll)                       |
+------------------------------------------------------------------+
| Similar Titles Slider (horizontal scroll)                        |
+------------------------------------------------------------------+
```

### TV Detail Page Differences

Same overall structure as movies, plus:
- **Season disclosure panels:** Collapsible sections for each season (reverse chronological order)
  - Episode count badge
  - Per-season status indicators (requested, pending, available, deleted)
  - Separate 4K status tracking per season
  - Expandable `<Season>` components
- **Completion tracking:** Show-level `isComplete` and `is4kComplete` calculated from season data
- **"Request More" button:** Available when show is partially requested

### Request Button Positioning

The request button lives in the `media-actions` container, which is **right-aligned in the header area** next to the title. On desktop, it appears as a prominent button. It is a `ButtonWithDropdown` (split button):
- **Main button:** Primary action (e.g., "Request")
- **Dropdown arrow:** Additional options (view request, approve, decline, 4K variants)

The split button uses indigo-600 styling with the main action and a chevron dropdown separator.

### Key Takeaway for Requestarr
A Lovelace card should NOT replicate the full detail page. The essential information for a request decision is: poster, title, year, overview (2-3 lines), and the request/status action. Everything else (cast, crew, ratings, streaming providers, similar titles) is discovery-oriented and better served by the actual Jellyseerr/TMDB interface. Keep the detail view minimal.

---

## 7. Mobile/Responsive Design

### Breakpoints (Tailwind defaults)

| Breakpoint | Width | Key Changes |
|-----------|-------|-------------|
| Base | < 640px | Mobile-first layout |
| `sm` | >= 640px | Minor adjustments |
| `md` | >= 768px | Card size increases (w-36 -> w-44) |
| `lg` | >= 1024px | Sidebar visible, bottom nav hidden |
| `xl` | >= 1280px | Request items switch to horizontal row |

### Mobile-Specific Adaptations

**Header:**
- Search bar takes most of the width
- Sidebar toggle button visible (hamburger icon)
- User dropdown condensed

**Navigation:**
- Bottom navigation bar replaces sidebar
- 4-5 items shown directly, overflow via ellipsis menu
- Outline icons when inactive, filled when active
- Touch-friendly tap targets

**Cards:**
- TitleCard width: 144px (vs 176px on desktop)
- Hover effects disabled; touch activates detail view
- Year hidden on RequestCard mobile view
- Action button labels abbreviated with tooltip support

**Modals:**
- Full-width on mobile (no max-width constraint)
- Center-aligned text and buttons
- Respects `safe-area-inset` for notched devices
- Max height: `calc(100% - env(safe-area-inset-top) * 2)`

**Request Cards:**
- Vertical stacking on mobile (< xl breakpoint)
- Horizontal row layout on xl+
- Backdrop images hidden on smaller screens

**Safe area handling:**
- Global CSS uses `env(safe-area-inset-*)` throughout
- Padding adjustments for fixed headers and bottom nav
- iOS notch compatibility built in

### PWA Support

Jellyseerr is installable as a Progressive Web App:
- Add to home screen on iOS/Android
- Near-native app experience
- HTTPS required for PWA installation
- PWA-specific back button in header
- Web push notification support

### Key Takeaway for Requestarr
A Lovelace card already lives inside HA's responsive framework. The card should target a minimum width of ~300px (phone in portrait) and work up to ~600px (tablet panel/wider layout). Touch interactions are paramount - no hover-dependent features. Safe area concerns are handled by HA's shell. The 144px card width on mobile is a good reference for poster thumbnails in a compact card layout.

---

## 8. Status Tracking

### "My Requests" / Request Management

**User Profile Page (`/profile`):**
- Dynamic backdrop from up to 6 random available titles (via `ImageFader`)
- Three stat cards:
  - Total requests (links to full history)
  - Movie request quota (remaining/limit with visual progress bar)
  - TV series request quota (remaining/limit with visual progress bar)
  - Quota cards highlight in red when exceeded
- Recent Requests slider (10 most recent as `RequestCard` horizontal scroll)
- Watchlist section (Plex or local)
- Recently Watched (Plex users only)

**Request List Page (`/requests`):**

**Filters:**
- Media type: All, Movie, TV
- Status: All, Pending, Approved, Completed, Processing, Failed, Available, Unavailable, Deleted
- Sort: Added (most recent) or Modified (last modified)
- Sort direction toggle (ascending/descending via arrow icon)

**Pagination:**
- Configurable page size: 5, 10, 25, 50, 100 items
- Previous/Next navigation buttons
- "Showing results X to Y of Z total" display
- Current page tracked via URL query parameter

**Per-Request Item Display:**
- Poster thumbnail (links to media detail page)
- Title + release year
- Season badges (TV shows)
- Status badge (color-coded)
- Request date with relative time + requester avatar
- Modification date (if edited)
- Profile name (if applicable)
- Action buttons based on permissions and status:
  - Pending: Approve/Decline (managers) or Edit (requester)
  - Failed: Retry (managers)
  - Completed: Delete / Remove from Arr
  - Personal: Cancel

**Filter persistence:** Saved to `localStorage`, restored on mount. URL params override stored values.

**Polling:** SWR re-fetches every 15 seconds when downloads are active.

### Request Statuses (Full Lifecycle)

```
User submits request
    |
    v
[PENDING] -- admin approves --> [APPROVED/PROCESSING]
    |                                    |
    | admin declines                     | Radarr/Sonarr downloads
    v                                    v
[DECLINED]                        [PROCESSING w/ progress]
                                         |
                                         | download completes
                                         v
                                    [AVAILABLE]
```

Additional states:
- **FAILED** - download or processing error
- **DELETED** - removed from library
- **PARTIALLY_AVAILABLE** - some seasons available (TV)

### Key Takeaway for Requestarr
For a household card, the "My Requests" view should be a simple list showing: title, status badge, and optionally a progress indicator. Filtering by status is overkill for 3-4 people with perhaps 5-20 active requests. The core statuses to surface are: Pending (yellow), Processing/Downloading (blue with %), Available (green), and Failed (red). A compact 3-5 item list with a "see all in Jellyseerr" link is sufficient.

---

## 9. Visual Design Language

### Color Palette

**Backgrounds:**
- Primary: `gray-900` (#111827) - main background
- Secondary: `gray-800` (#1f2937) - cards, surfaces
- Tertiary: `gray-700` (#374151) - borders, scrolled header

**Text:**
- Primary: `gray-300` (#d1d5db)
- Secondary: `gray-400` (#9ca3af)
- Emphasized: `gray-100` (#f3f4f6) / `white`
- Muted: `gray-500` (#6b7280)

**Accent:**
- Primary interactive: `indigo-600` (#4f46e5) - buttons, active states
- Active nav gradient: `from-indigo-600 to-purple-600`
- Links: `indigo-500` with `indigo-400` hover
- Focus rings: `indigo`

**Status colors:**
- Success: `green-500` (#22c55e)
- Warning: `yellow-500` (#eab308)
- Danger: `red-600` (#dc2626) / `red-500`
- Info/Primary: `indigo-500` (#6366f1)

### Typography

**Font:** Inter (sans-serif) with system fallback stack.

**Text sizes (Tailwind defaults):**
- `text-xs`: 0.75rem (12px) - badges, metadata
- `text-sm`: 0.875rem (14px) - body text, buttons
- `text-base`: 1rem (16px) - larger buttons
- Headings: variable sizes

**Badge text:** `text-xs font-semibold` in rounded-full pills.

### Spacing

- Card gap: `1rem` (16px) in grids
- Card padding: `px-2` (8px) in sliders
- Button padding: `px-4 py-2` (md), `px-2.5 py-1.5` (sm), `px-6 py-3` (lg)
- Modal padding: `px-4 pb-4 pt-4`

### Card Styling

- Background: `gray-800`
- Border: `ring-1 ring-gray-700`
- Rounded corners: `rounded-lg` (0.5rem / 8px)
- Poster images: `rounded-lg` with overflow hidden
- Hover: scale 105%, enhanced shadow

### Backdrop/Hero Images

- Full-width with gradient overlay: `linear-gradient(180deg, rgba(31,41,55,0.75) 0%, rgba(31,41,55,1) 100%)`
- Modal backdrops use the same gradient technique
- Discover page uses `ImageFader` for animated backdrop transitions

### Blur Effects

- Header: `backdrop-blur` when scrolled
- Sidebar overlay: `backdrop-blur` on mobile

### Scrollbar Customization

```css
/* Firefox */
scrollbar-width: thin;
scrollbar-color: #4b5563 #1f2937;

/* WebKit */
::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar-thumb { background: #4b5563; border-radius: 5px; }
::-webkit-scrollbar-thumb:hover { background: #6b7280; }
```

### Key Takeaway for Requestarr
The dark theme with gray-800/900 backgrounds and indigo accents fits naturally with HA's dark mode. For HA light mode, the card would need a separate theme. The Inter font, 16px gap, rounded-lg corners, and pill-shaped badges are all portable patterns. Use CSS custom properties / HA theme variables for colors rather than hardcoding the dark palette.

---

## 10. Key UX Patterns Worth Adopting or Avoiding

### ADOPT: Patterns That Work Well

**1. Search-as-you-type with debounce (300ms)**
Feels instant and responsive. Users do not need to press Enter or click Search. The 300ms debounce prevents excessive API calls while feeling nearly real-time.

**2. Status badge color system**
Green/Blue/Yellow/Red is universally understood. The pill-shaped badges with semi-transparent backgrounds are compact and readable at small sizes.

**3. Minimal request flow for regular users**
Without advanced permissions, requesting a movie is: click title -> click Request -> click Confirm. Three taps. This is excellent for non-technical household members.

**4. Auto-approval for trusted users**
Eliminates the "pending" bottleneck entirely. For a household of 3-4, auto-approve should be the default, reducing the flow to: click title -> click Request -> done (immediately processing).

**5. Poster-centric card design**
The 2:3 poster ratio is the universal standard for movie/TV art. Leading with the poster makes results instantly scannable - users recognize content visually before reading titles.

**6. Progress indication on downloads**
The colored bar overlay on status badges showing download percentage is elegant and information-dense without taking extra space.

**7. Inline status on search results**
Showing "Available" or "Requested" directly on title cards prevents users from clicking into something they already have.

### AVOID: Patterns That Are Over-Engineered for Household Use

**1. Full-page navigation with sidebar + bottom nav**
Jellyseerr has 8 navigation items. A household request card needs zero navigation - it should be a single view with search and status.

**2. Complex discover/trending page**
Multiple horizontal sliders of trending content, genre browsers, and admin-customizable sections add significant API overhead and complexity. For 3-4 people who usually know what they want to watch, a search bar is sufficient.

**3. Advanced requester options (server, profile, root folder, tags)**
These are power-user/admin features. A household card should use preconfigured defaults. If the admin wants 4K vs standard, that can be a simple toggle, not a server/profile dropdown.

**4. Granular permission system**
8 permission levels with bitwise flags. A household needs at most 2 roles: "can request" and "can manage". This should be handled by HA's existing user/admin system, not replicated in the card.

**5. Infinite scroll on search results**
Works well in a full web app but is awkward in a Lovelace card with limited height. A fixed number of results (5-8) with a "Show more" or "See in Jellyseerr" link is better.

**6. Full detail pages with cast, crew, ratings, recommendations**
This is a discovery tool, not a request tool. For requesting, users need: poster, title, year, brief overview, and a request button. Cast lists and streaming provider logos add bulk without aiding the request decision.

**7. TV season selection table for every request**
For household use, "Request All Available Seasons" should be the default with an option to customize. Most people want the whole show.

**8. Issue reporting and blocklist management**
These are admin tools that belong in Jellyseerr proper, not in a household request card.

### RECOMMENDED REQUESTARR UX FLOW

**Primary flow (optimized for household):**

```
[Always visible: Status list of active requests with badges]

[Search bar - pill-shaped, always visible]
         |
         | type query (300ms debounce)
         v
[Compact result list: 5-8 items]
[Each: poster thumb | title (year) | status badge]
         |
         | tap result
         v
[Inline detail expand or bottom sheet]
[Poster | Title | Year | 2-line overview]
[Request button (or status if already requested)]
[Optional: 4K toggle, season selector for TV]
         |
         | tap Request
         v
[Inline confirmation: "Requesting Movie Title..."]
[Status updates to "Requested" with blue badge]
```

**Click count targets:**
- Movie request: 3 taps (search already typed -> tap result -> tap request)
- TV show request (all seasons): 3 taps (same as movie, default to all)
- TV show request (specific seasons): 4-5 taps (add season selection step)

**Card dimensions recommendation:**
- Minimum width: 300px (phone portrait)
- Comfortable width: 400-500px
- Poster thumbnails in results: ~60px wide x 90px tall (scaled 2:3)
- Result row height: ~100px
- Status list item height: ~48px

---

## Appendix: Source Code References

Key source files examined from the Jellyseerr/Seerr repository:

| Component | Path | Purpose |
|-----------|------|---------|
| Search Page | `src/components/Search/index.tsx` | Search results page with ListView |
| Search Input | `src/components/Layout/SearchInput/index.tsx` | Pill-shaped search bar |
| useSearchInput | `src/hooks/useSearchInput.ts` | Search state management + URL routing |
| useDebouncedState | `src/hooks/useDebouncedState.ts` | 300ms debounce hook |
| TitleCard | `src/components/TitleCard/index.tsx` | Media result card (poster + info) |
| RequestModal | `src/components/RequestModal/index.tsx` | Request modal router |
| MovieRequestModal | `src/components/RequestModal/MovieRequestModal.tsx` | Movie request form |
| TvRequestModal | `src/components/RequestModal/TvRequestModal.tsx` | TV request form with seasons |
| RequestButton | `src/components/RequestButton/index.tsx` | Split button with dropdown |
| StatusBadge | `src/components/StatusBadge/index.tsx` | Color-coded status indicators |
| Badge | `src/components/Common/Badge/index.tsx` | Base badge component |
| Button | `src/components/Common/Button/index.tsx` | Button variants and sizes |
| ButtonWithDropdown | `src/components/Common/ButtonWithDropdown/index.tsx` | Split action button |
| ListView | `src/components/Common/ListView/index.tsx` | Grid results with infinite scroll |
| Slider | `src/components/Slider/index.tsx` | Horizontal media slider |
| Modal | `src/components/Common/Modal/index.tsx` | Base modal with backdrop |
| Layout | `src/components/Layout/index.tsx` | App shell with sidebar + header |
| Sidebar | `src/components/Layout/Sidebar/index.tsx` | Desktop navigation |
| MobileMenu | `src/components/Layout/MobileMenu/index.tsx` | Mobile bottom nav |
| MovieDetails | `src/components/MovieDetails/index.tsx` | Movie detail page |
| TvDetails | `src/components/TvDetails/index.tsx` | TV show detail page |
| Discover | `src/components/Discover/index.tsx` | Discover page with sliders |
| RequestList | `src/components/RequestList/index.tsx` | Request management page |
| RequestCard | `src/components/RequestCard/index.tsx` | Individual request card |
| RequestItem | `src/components/RequestList/RequestItem/index.tsx` | Request list row |
| UserProfile | `src/components/UserProfile/index.tsx` | User dashboard |
| globals.css | `src/styles/globals.css` | Global styles + grid definitions |
| tailwind.config.js | `tailwind.config.js` | Theme configuration |
