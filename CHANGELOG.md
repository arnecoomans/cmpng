# Changelog

## [Unreleased]

### Added
- Staff dashboard at `/staff/dashboard/` — surfaces locations needing attention across eight cards: problems (missing address or region), lowest completeness score, missing/short summary, missing description, fewest tags, fewest categories, recently commented, recently added, and revoked locations. The problems card is full-width and only renders when issues exist. Locations with the "home" category are excluded from all cards except revoked. Revoked locations are sorted by missing reason first, then by date. Linked from the staff section of the navigation dropdown. ([#2](https://github.com/arnecoomans/cmpng/issues/2), [#15](https://github.com/arnecoomans/cmpng/issues/15))
- `Tag.similarity_weight` field (default 100) — tags that strongly define a location's character (e.g. *domaine*, *Nederlandse eigenaren*) can be given a higher weight to increase their contribution to the similarity score. Editable in Django admin and the tag edit form. ([#39](https://github.com/arnecoomans/cmpng/issues/39))

### Changed
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
