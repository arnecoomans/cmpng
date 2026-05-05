# API Endpoints

## `?format=filters` — filter options JSON

**Available on:** all location list views (`/all/`, `/accommodations/`, `/activities/`) and map views (`/all/map/`, etc.)

**Defined in:** `LocationListMasterView._filters_json_response()` (`locations/views/locations/locations_list.py`)

### Request

```
GET /all/?format=filters
GET /accommodations/?format=filters&category=camping
GET /all/map/?format=filters&coord_lat__gte=51.0&coord_lat__lte=52.0&coord_lon__gte=4.0&coord_lon__lte=6.0
```

All regular filter parameters (`country`, `region`, `category`, `tag`, `is_visited`, etc.) and viewport bounding-box parameters (`coord_lat__gte`, `coord_lat__lte`, `coord_lon__gte`, `coord_lon__lte`) are respected. Viewport params are applied to the queryset but stripped from the option URLs returned in the response.

### Response

```json
{
  "category": {
    "options": [{ "slug": "camping", "name": "Camping", "count": 12, "url": "..." }],
    "all_options": [...]
  },
  "tag": {
    "options": [{ "slug": "pool", "name": "Pool", "count": 5, "url": "..." }],
    "all_options": [...]
  },
  "types": {
    "accommodations": true,
    "activities": false
  }
}
```

`options` — filtered to the current queryset (respects active filters + viewport).  
`all_options` — unfiltered (full scope of the view, e.g. accommodations-only on `/accommodations/`).  
`types` — based on the unscoped `_optimized_queryset` so the accommodation/activity pills never incorrectly disable.

### Current usage

- **Map views** — called after pan/zoom (`idle` event) and after filter changes to update category/tag autosuggests and type availability without a page reload.
- **List views** — endpoint is available but not yet wired to anything on the page. Could drive dynamic filter panel updates after a geo filter change (e.g. refreshing category options after selecting a country). ([#48](https://github.com/arnecoomans/cmpng/issues/48))
