# Changelog

## [Unreleased]

### Added
- **Upcoming visits widget** on the location list page — authenticated users with `show_upcoming_visits` enabled see a lazy-loaded ribbon above results showing planned visits within the next 6 months. `Visits.upcoming(user, months_ahead=6)` classmethod handles the date window including year wrap, filters `status='p'`, and orders by `year, month, day`. `UserPreferences.upcoming_visits` (`@ajax_login_required`) drives the cmnsd dispatch; the widget is injected via `cmnsd.loadContent` on `cmnsdPostInit` and Bootstrap popovers are re-initialised via `cmnsd:content:applied`. An `(i)` button on the right of the header opens a popover explaining visibility and linking to preferences. Toggle controlled by `show_upcoming_visits` BooleanField (default `True`). ([#45](https://github.com/arnecoomans/cmpng/issues/45))
- **sorl-thumbnail** added for bandwidth-efficient thumbnails. List page, nearby, and similar templates now serve 144×96 px server-side crops (2× retina) instead of full-size images scaled in CSS. An empty migration (`0011_add_sorl_thumbnail`) with a dependency on sorl's own migration ensures `update.sh` triggers `manage.py migrate` on deploy without any script changes. ([#57](https://github.com/arnecoomans/cmpng/issues/57))

### Changed
- Green accent reduced to interactive states, badges, and section indicators — page shell now white/light-gray. Results header bar is transparent with a gray count pill; country section headers are compact rounded pills (not full-width bars). ([#50](https://github.com/arnecoomans/cmpng/issues/50))
- Geographic hierarchy in the location list is now visually distinct across all three levels: country (dark green chip with flag emoji), region (green left-rule, `font-weight: 700`, `--text-sm`), department (gray left-rule, uppercase, `--text-xs`, `--gray-600` for readable contrast). `Region.flag_emoji` property derives the flag from the ISO country slug. ([#53](https://github.com/arnecoomans/cmpng/issues/53))
- Location cards on the list page now show a 72×48 px thumbnail on the left. Locations with media show a cropped image (visibility-aware: authenticated users see community+public media, anonymous users see public only). Locations without media show an initial-letter placeholder with a gradient — green for accommodations, purple for activities, gray otherwise. Cards collapse to single-column on mobile (< 480 px) and thumbnails are hidden. `Location.thumb` property added; `request` injected onto each location in `get_context_data` to gate community visibility. ([#52](https://github.com/arnecoomans/cmpng/issues/52))
- Detail page map card and nearby/similar sections improved: map canvas reduced to 260px; Apple Maps / Google Maps / Waze navigation links added to the map card footer (shown when address is set); nearby and similar accordion buttons show a cached item count (Django cache, 1-hour TTL, set on first accordion open — zero extra DB queries on page load); nearby/similar thumbnails replaced with visibility-aware `loc.thumb`; fold columns changed to 50/50. ([#55](https://github.com/arnecoomans/cmpng/issues/55))
- Detail page layout and hierarchy improved: breadcrumb gains a `← All locations` back-link (green, bold) to the unfiltered type list; completeness badge demoted to 11px/60% opacity so it no longer competes with the title; summary text bumped to `--text-lg` with relaxed line-height and more breathing room before the fold; fold column proportions widened to `1.15fr .85fr`; staff-only actions (re-enrich, revoke, admin view) collapsed into a `⋮` dropdown to reduce topactions bar width. ([#54](https://github.com/arnecoomans/cmpng/issues/54))
- Sidebar filter controls unified to a single pill component across all toggle-style filters (Type, Visited, Favourited, Visibility, Status). Middot separators removed. Visited and Favourited render as a horizontal inline row; remaining filters use a vertical grid. Type filter counts omitted — they were misleading for dual-categorised locations. Active geo breadcrumb now shows the translated `Region.name` instead of the raw URL slug. ([#51](https://github.com/arnecoomans/cmpng/issues/51))
- Removed the full-bleed green hero header — replaced with an opt-in `{% block hero %}` so other apps can keep it while cmpng renders nothing above the navbar. ([#49](https://github.com/arnecoomans/cmpng/issues/49))
- Navbar redesigned as a single consolidated header: inline tent SVG in the brand link, sentence navigation ("Go somewhere …to stay …to do") with correct scope-based active state, pill-shaped search input with inline icon, white background with subtle border. Eliminates the duplicate brand name and the green gradient that dominated the palette. ([#49](https://github.com/arnecoomans/cmpng/issues/49))
- "Go somewhere" prefix hides on viewports narrower than 900px; sentence links remain visible. ([#49](https://github.com/arnecoomans/cmpng/issues/49))
- Replaced system font stack with self-hosted **Geist** variable font (woff2, `font-display: swap`) for consistent rendering across all platforms. GeistMono applied to `code`, `pre`, `kbd`, `samp`. ([#56](https://github.com/arnecoomans/cmpng/issues/56))
- Added complete type scale (`--text-xs` through `--text-3xl`), line-height (`--leading-tight` through `--leading-loose`), and letter-spacing (`--tracking-tight` through `--tracking-widest`) tokens to `root.css`. ([#56](https://github.com/arnecoomans/cmpng/issues/56))
- Body text set to 15px (`--text-base`) with line-height 1.6 (`--leading-normal`) and font smoothing; headings use `--tracking-tight` and `--leading-tight` consistently. ([#56](https://github.com/arnecoomans/cmpng/issues/56))
- `.location-summary` and `.description__body` constrained to `max-width: 68ch` for optimal line length; `font-weight: 550` replaced with `var(--fw-medium)`. ([#56](https://github.com/arnecoomans/cmpng/issues/56))
- `.card__title` and `.cmpng-sidebar h2` migrated to type scale tokens — `--text-xs`, weight 800, `--tracking-wider`, uppercase — consistent section label pattern site-wide. ([#56](https://github.com/arnecoomans/cmpng/issues/56))

## [26.04.3] - 2026-05-04

### Added
- Interactive map view for location lists — full-viewport Google Maps interface with a floating filter panel for type (all / accommodations / activities), visited, favourited, visibility, category, and tag filters. Filter changes update markers in-place via `pushState` without a page reload. After the initial load (which auto-fits all results), panning or zooming triggers viewport-bounded marker fetches so only locations in the visible area are loaded. Filter options (category/tag autosuggests, type availability) also update to reflect the current viewport. Map views are restricted to authenticated users. Available at `/all/map/`, `/accommodations/map/`, `/activities/map/`. ([#37](https://github.com/arnecoomans/cmpng/issues/37))
- Tag parent field on the tag edit form — autosuggest filtered to top-level tags only (`parent__isnull=true`); includes a × button to clear the parent via cmnsd.api without leaving the page. ([#43](https://github.com/arnecoomans/cmpng/issues/43))
- Staff dashboard at `/staff/dashboard/` — surfaces locations needing attention across eight cards: problems (missing address or region), lowest completeness score, missing/short summary, missing description, fewest tags, fewest categories, recently commented, recently added, and revoked locations. The problems card is full-width and only renders when issues exist. Locations with the "home" category are excluded from all cards except revoked. Revoked locations are sorted by missing reason first, then by date. Linked from the staff section of the navigation dropdown. ([#2](https://github.com/arnecoomans/cmpng/issues/2), [#15](https://github.com/arnecoomans/cmpng/issues/15))
- `Tag.similarity_weight` field (default 100) — tags that strongly define a location's character (e.g. *domaine*, *Nederlandse eigenaren*) can be given a higher weight to increase their contribution to the similarity score. Editable in Django admin and the tag edit form. ([#39](https://github.com/arnecoomans/cmpng/issues/39))

### Changed
- Visibility filter in the location list filterbox is now suppressed entirely for anonymous users — they can only ever see public content, so the filter carried no information; authenticated users see it unchanged
- Completely rewrote the filter box to work more simple, effective and logically.
- Manage tag visibility moved from `/manage/tags/` to `/staff/tags/` to consolidate staff-only URLs under the `/staff/` prefix
- Similar locations: negative community recommendation score now deducts −0.10 from the composite score (mirrors the +0.10 bonus for positive scores) ([#39](https://github.com/arnecoomans/cmpng/issues/39))
- Similar locations: locations the authenticated user has personally marked as "not recommended" are never shown in their similar list, regardless of community score or attribute overlap ([#39](https://github.com/arnecoomans/cmpng/issues/39))

### Fixed
- Topactions bar no longer overflows on mobile — buttons wrap with `flex-wrap`, staff-only actions (re-enrich, revoke, admin view) break to a second row on small screens ([#40](https://github.com/arnecoomans/cmpng/issues/40))
- Nearby and similar thumbnails now respect media visibility — `request` is propagated onto each returned location object so `ordered_media` applies the correct visibility filter; previously all media including private and family photos were exposed ([#42](https://github.com/arnecoomans/cmpng/issues/42))

## [26.04.2] - 2026-04-12

### Added
- Similar locations — `Location.similar()` method and `get_similar_locations()` service surface globally similar locations using a composite score: tag/category overlap (base), same chain (+0.20), any chain (+0.05), same size (+0.10), adjacent size (+0.05), positive community recommendation (+0.10), any favourite (+0.05). Restricted to the same country by default (`SIMILAR_SAME_COUNTRY = True`). Exposed via cmnsd API as `similar.json` / `similar.html`. Displayed on the location detail page as a lazy-loaded Bootstrap accordion. Anonymous users see up to 5 results with a register/login nudge if more exist. ([#9](https://github.com/arnecoomans/cmpng/issues/9))
- Nearby and similar sections on the location detail page are now lazy-loaded Bootstrap accordions — both closed by default, content fetched on first open via `show.bs.collapse` event ([#9](https://github.com/arnecoomans/cmpng/issues/9))
- Two-level community recommendation scoring: each user's visits are averaged first, then those per-user averages are averaged — prevents repeat visitors from dominating the score. Applied to `get_visit_context()`, `get_recommendation_summary()`, and the `with_visit_state()` queryset annotation ([#34](https://github.com/arnecoomans/cmpng/issues/34))
- Recommendation score column added to `LocationAdmin` list display, showing the two-level community average per location
- Human-readable recommendation label added to `VisitsAdmin` list display (Recommended / Neutral / Not recommended)
- GDPR data export: authenticated users can download a ZIP archive of CSVs covering visits, comments, locations added, media added, lists, and profile & preferences. Available via the preferences page. ([#33](https://github.com/arnecoomans/cmpng/issues/33))
- Map viewport filtering on the location detail page — nearby markers load dynamically from the JSON endpoint as the user pans or zooms; uses the Maps `idle` event so markers update only after the viewport settles ([#4](https://github.com/arnecoomans/cmpng/issues/4))
- Post-close page refresh for modals — `data-on-close-url` and `data-on-close-map` attributes on any modal trigger cause the specified page sections to be re-fetched and updated when the modal closes, without a full page reload ([#25](https://github.com/arnecoomans/cmpng/issues/25))

### Fixed
- `Tag` default visibility is now hardcoded to `'c'` (community) regardless of the `DEFAULT_MODEL_VISIBILITY` setting ([#30](https://github.com/arnecoomans/cmpng/issues/30))
- [Bugfix] Visits with `status != 'p'` (revoked or deleted) were incorrectly included in visit indicators, recommendation scores, and community averages; all visit queries now filter on `status='p'` ([#38](https://github.com/arnecoomans/cmpng/issues/38))

## [26.04.1] - 2026-04-04

> ⚠️ **Migration required:** run `python manage.py migrate`, `python manage.py update_completeness` to backfill completeness scores, and `python manage.py backfill_media_hashes` to backfill file hashes for existing media.

### Added
- Completeness score (0–100) on `Location` — normalised against applicable criteria with bonuses for visited (+10%) and listed (+10%), capped at 100. Shown as a colour-coded badge with click-to-expand hints on the location detail page for authenticated users. Recalculated automatically via signals on save. Staff dashboard integration pending. ([#15](https://github.com/arnecoomans/cmpng/issues/15))
- Optional end date (`end_year`, `end_month`, `end_day`) on `Visits` — shown as a date range in the visit list with night count. Add-visit form has a collapsible end date section, hidden by default. ([#7](https://github.com/arnecoomans/cmpng/issues/7))
- Uploaded media filenames are now prefixed with the upload date (`yyyy-mm-dd-filename.jpg`) to prevent overwrites and aid media management ([#26](https://github.com/arnecoomans/cmpng/issues/26))
- When a location is created without a URL, a Google search link is automatically added as the first link ([#24](https://github.com/arnecoomans/cmpng/issues/24))
- When the "home" category is added to a location, visibility is automatically forced to "family" via signal. The add-location form shows an info message when this occurs. On the detail page, the visibility field reloads immediately via AJAX alongside the category field ([#27](https://github.com/arnecoomans/cmpng/issues/27))
- Duplicate media uploads are now prevented: the upload button is disabled on submit and re-enabled on error (client-side); server-side, a SHA-256 hash of the file is stored on `Media` and duplicate uploads to the same location are silently dropped, with a warning message returned ([#23](https://github.com/arnecoomans/cmpng/issues/23))

### Changed
- Moved all management URLs under `/manage/` prefix (`manage/media/`, `manage/visits/`, `manage/lists/`, `manage/tags/`) to avoid nginx collision with the `/media/` static file directory ([#20](https://github.com/arnecoomans/cmpng/issues/20))

### Fixed
- Lists view now shows the list owner as a badge when the list belongs to another user ([#21](https://github.com/arnecoomans/cmpng/issues/21))
- Manage tag visibility now shows only published leaf tags; parent tags and non-published tags are excluded. View is staff-only ([#22](https://github.com/arnecoomans/cmpng/issues/22))
- [Bugfix] Google search link display names now decode percent-encoded characters (e.g. `Camping%20Test` → `Camping Test on Google`) using `urllib.parse.parse_qs` ([#28](https://github.com/arnecoomans/cmpng/issues/28))
- [Bugfix] Completeness signals now skip recalculation during fixture loading (`raw=True`) — prevented `loaddata` from failing when related objects had not yet been loaded
- [Bugfix] Increased `Location.phone` max length from 20 to 50 characters to support formatted international numbers (e.g. `+31 (0)6 – 50 40 96 75`)
- [Bugfix] Fixed white-on-white text in lists view — `.badge`, `.badge--muted`, and `.hint` were scoped to the detail page CSS only; moved to global stylesheet
- [Bugfix] Test media files no longer accumulate in the project `media/` directory — `conftest.py` now redirects `MEDIA_ROOT` to a per-test temp directory via an `autouse` fixture

## [26.04] - 2026-04-02

Initial release. See [release notes](https://github.com/arnecoomans/cmpng/releases/tag/v26.04).
