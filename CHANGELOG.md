# Changelog

## [Unreleased]

> ⚠️ **Migration required:** run `python manage.py migrate` and `python manage.py update_completeness` to backfill scores for existing locations.

### Added
- Completeness score (0–100) on `Location` — normalised against applicable criteria with bonuses for visited (+10%) and listed (+10%), capped at 100. Shown as a colour-coded badge with click-to-expand hints on the location detail page for authenticated users. Recalculated automatically via signals on save. Staff dashboard integration pending. ([#15](https://github.com/arnecoomans/cmpng/issues/15))
- Optional end date (`end_year`, `end_month`, `end_day`) on `Visits` — shown as a date range in the visit list with night count. Add-visit form has a collapsible end date section, hidden by default. ([#7](https://github.com/arnecoomans/cmpng/issues/7))

### Changed
- Moved all management URLs under `/manage/` prefix (`manage/media/`, `manage/visits/`, `manage/lists/`, `manage/tags/`) to avoid nginx collision with the `/media/` static file directory ([#20](https://github.com/arnecoomans/cmpng/issues/20))

### Fixed
- [Bugfix] Increased `Location.phone` max length from 20 to 50 characters to support formatted international numbers (e.g. `+31 (0)6 – 50 40 96 75`)
-  Lists view now shows the list owner as a badge when the list belongs to another user ([#21](https://github.com/arnecoomans/cmpng/issues/21))
- [Bugfix] Fixed white-on-white text in lists view — `.badge`, `.badge--muted`, and `.hint` were scoped to the detail page CSS only; moved to global stylesheet
- Manage tag visibility now shows only published leaf tags; parent tags and non-published tags are excluded. View is staff-only ([#22](https://github.com/arnecoomans/cmpng/issues/22))

## [26.04] - 2026-04-02

Initial release. See [release notes](https://github.com/arnecoomans/cmpng/releases/tag/v26.04).
