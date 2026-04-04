# Changelog

## [Unreleased]

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
