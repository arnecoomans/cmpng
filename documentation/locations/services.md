# Services Reference - Locations App

Complete reference for all service modules in the locations app.

## Overview

The service layer contains business logic separated from models. Services handle:
- Complex queries and aggregations
- External API interactions
- Business calculations
- Batch operations

## Table of Contents

- [location_queries](#location_queries)
- [location_geocoding](#location_geocoding)
- [location_distance](#location_distance)

---

## location_queries

**File:** `locations/services/location_queries.py`

Query builders and aggregation functions for extracting filter options from location querysets.

### Functions

#### `get_tags_from_queryset(queryset, limit=20, min_usage=1)`

Extract unique tags from a location queryset, ordered by usage count.

**Parameters:**
- `queryset` (QuerySet) - Location queryset to extract tags from
- `limit` (int, optional) - Maximum number of tags to return. Default: 20. Set to `None` for unlimited.
- `min_usage` (int, optional) - Minimum number of locations that must use the tag. Default: 1.

**Returns:**
- QuerySet of dicts with keys: `id`, `slug`, `name`, `location_count`

**Filters:**
- Only includes published tags (`status='p'`)
- Excludes tags used by fewer than `min_usage` locations
- Returns distinct tags (no duplicates)

**Ordering:**
- Primary: By usage count (descending) - most popular first
- Secondary: By name (alphabetical)

**Example:**
```python
from locations.services.location_queries import get_tags_from_queryset
from locations.models import Location

# Get top 10 most popular tags for Dutch locations
dutch_locations = Location.objects.filter(region__parent__parent__slug='nl')
tags = get_tags_from_queryset(dutch_locations, limit=10, min_usage=2)

for tag in tags:
    print(f"{tag['name']}: used by {tag['location_count']} locations")
    # Output: "Pet Friendly: used by 15 locations"
```

**SQL Generated:**
```sql
SELECT tag.id, tag.slug, tag.name, COUNT(DISTINCT location.id) as location_count
FROM tag
INNER JOIN location_tags ON tag.id = location_tags.tag_id
WHERE location_tags.location_id IN (/* queryset */)
  AND tag.status = 'p'
GROUP BY tag.id
HAVING COUNT(DISTINCT location.id) >= 2
ORDER BY location_count DESC, tag.name ASC
LIMIT 10
```

**Use Cases:**
- Populate filter dropdown with relevant tags
- Show popular tags in sidebar
- Display tag cloud
- Build faceted search interface

---

#### `get_categories_from_queryset(queryset, limit=20, min_usage=1)`

Extract unique categories from a location queryset, ordered by usage count.

**Parameters:** Same as `get_tags_from_queryset()`

**Returns:** Same structure as `get_tags_from_queryset()`

**Example:**
```python
from locations.services.location_queries import get_categories_from_queryset

# Get categories for camping locations
camping_locations = Location.objects.filter(categories__slug='camping')
categories = get_categories_from_queryset(camping_locations, limit=15)

for cat in categories:
    print(f"{cat['name']}: {cat['location_count']} locations")
```

**Use Cases:**
- Category filter dropdowns
- Breadcrumb navigation
- Related categories suggestions

---

#### `get_countries_with_locations(queryset=None)`

Get all unique countries (top-level regions) that have locations.

**Parameters:**
- `queryset` (QuerySet, optional) - Location queryset to extract countries from. Default: `None` (all locations).

**Returns:**
- QuerySet of dicts with keys:
  - `region__parent__parent__id` - Country ID
  - `region__parent__parent__slug` - Country slug
  - `region__parent__parent__name` - Country name

**Filters:**
- Excludes locations without a country (missing region hierarchy)
- Returns distinct countries

**Ordering:** Alphabetical by country name

**Example:**
```python
from locations.services.location_queries import get_countries_with_locations

# Get all countries with any locations
countries = get_countries_with_locations()

for country in countries:
    print(country['region__parent__parent__name'])
    # Output: "Belgium", "France", "Netherlands"

# Get countries for filtered queryset
activity_locations = Location.objects.filter(is_activity=True)
activity_countries = get_countries_with_locations(activity_locations)
```

**Use Cases:**
- Country filter dropdown
- Map marker clustering by country
- Statistics by country

---

#### `get_regions_with_locations(queryset=None)`

Get all unique regions (second-level hierarchy) that have locations.

**Parameters:** Same as `get_countries_with_locations()`

**Returns:**
- QuerySet of dicts with keys:
  - `region__parent__id` - Region ID
  - `region__parent__slug` - Region slug
  - `region__parent__name` - Region name

**Example:**
```python
from locations.services.location_queries import get_regions_with_locations

# Get regions for Dutch locations
dutch_locations = Location.objects.filter(region__parent__parent__slug='nl')
regions = get_regions_with_locations(dutch_locations)

for region in regions:
    print(region['region__parent__name'])
    # Output: "Utrecht", "Gelderland", "Noord-Holland"
```

**Use Cases:**
- Cascading dropdown (country → region)
- Regional statistics
- Regional map views

---

#### `get_departments_with_locations(queryset=None)`

Get all unique departments (third-level hierarchy) that have locations.

**Parameters:** Same as `get_countries_with_locations()`

**Returns:**
- QuerySet of dicts with keys:
  - `region__id` - Department ID
  - `region__slug` - Department slug
  - `region__name` - Department name

**Example:**
```python
from locations.services.location_queries import get_departments_with_locations

# Get departments in Utrecht region
utrecht_locations = Location.objects.filter(region__parent__slug='utrecht')
departments = get_departments_with_locations(utrecht_locations)

for dept in departments:
    print(dept['region__name'])
    # Output: "Bunnik", "Houten", "Zeist"
```

**Use Cases:**
- Cascading dropdown (country → region → department)
- Detailed geographic filtering
- Local area exploration

---

### Performance Notes

All query functions in this module:
- Execute a **single database query** (no N+1 problems)
- Use `distinct()` to avoid duplicates
- Use `values()` to return only necessary fields (smaller result sets)
- Are optimized for large datasets

**Benchmark (1000 locations, 50 tags):**
- `get_tags_from_queryset()`: ~15ms
- Without optimization (N+1 queries): ~500ms

---

## location_geocoding

**File:** `locations/services/location_geocoding.py`

Google Maps API integration for geocoding addresses.

### Functions

#### `geocode_location(location, request=None)`

Geocode a single location's address and update its coordinates.

**Parameters:**
- `location` (Location) - Location instance to geocode
- `request` (HttpRequest, optional) - Django request for user messages

**Returns:**
- `(latitude, longitude)` tuple if successful
- `None` if geocoding failed

**Side Effects:**
- Updates `location.coord_lat` and `location.coord_lon`
- Saves location with `update_fields=['coord_lat', 'coord_lon']`
- Adds messages to request (success/warning/error)

**Requirements:**
- `location.address` must be set
- `settings.GOOGLE_API_KEY` must be configured

**Example:**
```python
from locations.services.location_geocoding import geocode_location

location = Location.objects.get(slug='camping-paradise')
location.address = '123 Main St, Amsterdam, Netherlands'
location.save()

result = geocode_location(location, request=request)

if result:
    lat, lon = result
    print(f"Geocoded: {lat}, {lon}")
    # Coordinates are automatically saved to location
else:
    print("Geocoding failed")
```

**With Django messages:**
```python
# In a view
def geocode_view(request, location_id):
    location = Location.objects.get(id=location_id)
    geocode_location(location, request=request)
    # User sees: "Geocoded Camping Paradise: 52.3676, 4.9041"
    return redirect('location_detail', slug=location.slug)
```

**Error Handling:**
```python
try:
    result = geocode_location(location, request=request)
except GeocoderQueryError as e:
    # Error message already added to request
    logger.error(f"Geocoding failed for {location.name}: {e}")
```

**Messages Generated:**
- Success: "Geocoded {location.name}: {lat}, {lon}"
- Warning: "No address provided for {location.name}"
- Warning: "Could not geocode address: {address}"
- Error: "Geocoding error for {location.name}: {error}"

---

#### `geocode_multiple_locations(queryset, request=None)`

Batch geocode multiple locations.

**Parameters:**
- `queryset` (QuerySet) - Location queryset to geocode
- `request` (HttpRequest, optional) - Django request for user messages

**Returns:**
- Dict with keys:
  - `success` (int) - Number of successfully geocoded locations
  - `failed` (int) - Number of failed geocoding attempts
  - `skipped` (int) - Number of locations skipped (already have coordinates)

**Filters:**
- Only processes locations with:
  - `coord_lat__isnull=True`
  - `coord_lon__isnull=True`
  - `address__isnull=False`
  - `address != ''`

**Example:**
```python
from locations.services.location_geocoding import geocode_multiple_locations

# Geocode all locations without coordinates
locations = Location.objects.filter(
    coord_lat__isnull=True,
    address__isnull=False
)

results = geocode_multiple_locations(locations, request=request)

print(f"Successfully geocoded: {results['success']}")
print(f"Failed: {results['failed']}")
print(f"Skipped: {results['skipped']}")
```

**In a management command:**
```python
# management/commands/geocode_all.py
from django.core.management.base import BaseCommand
from locations.services.location_geocoding import geocode_multiple_locations
from locations.models import Location

class Command(BaseCommand):
    def handle(self, *args, **options):
        locations = Location.objects.filter(status='p')
        results = geocode_multiple_locations(locations)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Geocoded {results['success']} locations"
            )
        )
```

**Rate Limiting:**

Google Maps API has rate limits. For large batches:
```python
import time

# Process in chunks with delays
chunk_size = 50
locations = Location.objects.filter(coord_lat__isnull=True)

for i in range(0, locations.count(), chunk_size):
    chunk = locations[i:i+chunk_size]
    results = geocode_multiple_locations(chunk)
    print(f"Batch {i//chunk_size + 1}: {results['success']} succeeded")
    
    if i + chunk_size < locations.count():
        time.sleep(2)  # Avoid rate limits
```

---

### Configuration

**Required Settings:**
```python
# settings.py
GOOGLE_API_KEY = 'your-google-maps-api-key'
```

**Google Maps API Setup:**

1. Enable "Geocoding API" in Google Cloud Console
2. Create API key with restrictions:
   - API restrictions: Geocoding API only
   - Application restrictions: Your domain
3. Set monthly budget/quota limits

**Cost Estimation:**

- Google Geocoding API: $5 per 1000 requests (first 40k/month free)
- Average: 1000 locations = ~$5 (after free tier)

---

## location_distance

**File:** `locations/services/location_distance.py`

Distance calculations from departure center using geopy.

### Functions

#### `calculate_distance_to_departure_center(location, request=None)`

Calculate and cache distance from departure center for a single location.

**Parameters:**
- `location` (Location) - Location instance
- `request` (HttpRequest, optional) - Django request for user messages

**Returns:**
- Distance in kilometers (int) if successful
- `None` if calculation failed

**Side Effects:**
- Updates `location.distance_to_departure_center`
- Saves location with `update_fields=['distance_to_departure_center']`
- Triggers `region.calculate_average_distance_to_center()` if distance changed
- Adds messages to request

**Requirements:**
- `location.coord_lat` and `location.coord_lon` must be set
- `settings.DEPARTURE_CENTER` must be configured

**Automatic Geocoding:**

If coordinates are missing but address exists, attempts to geocode first:
```python
location.coord_lat = None
location.address = 'Amsterdam, Netherlands'

# Will automatically geocode, then calculate distance
distance = calculate_distance_to_departure_center(location)
```

**Example:**
```python
from locations.services.location_distance import calculate_distance_to_departure_center

location = Location.objects.get(slug='camping-paradise')
distance = calculate_distance_to_departure_center(location, request=request)

if distance:
    print(f"Distance: {distance} km")
    # Distance is automatically saved to location.distance_to_departure_center
```

**With Region Cascade:**

When a location's distance changes, it triggers recalculation for all ancestor regions:
```python
# Before
location.distance_to_departure_center  # None
location.region.cached_average_distance_to_center  # 0

# Calculate
calculate_distance_to_departure_center(location)

# After
location.distance_to_departure_center  # 150
location.region.cached_average_distance_to_center  # 148 (average of all children)
location.region.parent.cached_average_distance_to_center  # 145 (average of regions)
```

---

#### `recalculate_all_distances(queryset=None, request=None)`

Batch recalculate distances for multiple locations.

**Parameters:**
- `queryset` (QuerySet, optional) - Location queryset. Default: all locations with coordinates.
- `request` (HttpRequest, optional) - Django request for user messages

**Returns:**
- Dict with keys:
  - `calculated` (int) - Successfully calculated distances
  - `skipped` (int) - Locations without coordinates
  - `failed` (int) - Failed calculations

**Default Queryset:**

If no queryset provided, uses:
```python
Location.objects.filter(
    coord_lat__isnull=False,
    coord_lon__isnull=False
)
```

**Example:**
```python
from locations.services.location_distance import recalculate_all_distances

# Recalculate all
stats = recalculate_all_distances()
print(f"Calculated: {stats['calculated']}")
print(f"Skipped: {stats['skipped']}")
print(f"Failed: {stats['failed']}")

# Recalculate specific country
dutch_locations = Location.objects.filter(
    region__parent__parent__slug='nl',
    coord_lat__isnull=False
)
stats = recalculate_all_distances(dutch_locations)
```

**In a management command:**
```python
# management/commands/calculate_distances.py
from django.core.management.base import BaseCommand
from locations.services.location_distance import recalculate_all_distances

class Command(BaseCommand):
    help = 'Calculate distances for all locations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recalculate even if distance already exists'
        )

    def handle(self, *args, **options):
        if options['force']:
            queryset = Location.objects.filter(
                coord_lat__isnull=False,
                coord_lon__isnull=False
            )
        else:
            queryset = Location.objects.filter(
                coord_lat__isnull=False,
                coord_lon__isnull=False,
                distance_to_departure_center__isnull=True
            )
        
        stats = recalculate_all_distances(queryset)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Calculated {stats['calculated']} distances"
            )
        )
```

---

### Configuration

**Required Settings:**
```python
# settings.py
DEPARTURE_CENTER = 'Geldermalsen, Gelderland, Netherlands'
```

**Changing Departure Center:**
```python
# Old setting
DEPARTURE_CENTER = 'Amsterdam, Netherlands'

# After changing
DEPARTURE_CENTER = 'Brussels, Belgium'

# Recalculate all distances
from locations.services.location_distance import recalculate_all_distances
recalculate_all_distances(Location.objects.all())
```

**Distance Calculation Method:**

Uses **great-circle distance** (haversine formula) via `geopy.distance`:
```python
from geopy import distance

# Example calculation
departure = (52.0, 5.0)  # Geldermalsen
destination = (52.3676, 4.9041)  # Amsterdam

dist = distance.distance(departure, destination)
print(f"{dist.km} km")  # Output: "41.2 km"
```

**Accuracy:**
- Great-circle distance: ~99.5% accurate for short distances (<1000 km)
- For very long distances, geodesic distance is more accurate (negligible difference for European travel)

---

## Utility Functions

### `get_departure_coordinates()`

**File:** `locations/utils/geo.py`

Get departure center coordinates with caching.

**Returns:**
- `(latitude, longitude)` tuple if successful
- `None` if geocoding failed

**Caching:**
- Caches result for 30 days
- Cache key: `departure_coords_{settings.DEPARTURE_CENTER}`
- Uses Django's cache framework

**Example:**
```python
from locations.utils.geo import get_departure_coordinates

coords = get_departure_coordinates()
if coords:
    lat, lon = coords
    print(f"Departure center: {lat}, {lon}")
```

**Cache Invalidation:**
```python
from django.core.cache import cache

# Clear cached coordinates
cache.delete(f'departure_coords_{settings.DEPARTURE_CENTER}')

# Next call will geocode again
coords = get_departure_coordinates()
```

---

## Service Usage Patterns

### Pattern 1: View Integration
```python
# views/locations/list.py
from locations.services.location_queries import (
    get_tags_from_queryset,
    get_categories_from_queryset,
    get_countries_with_locations
)

class LocationListView(ListView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        
        # Get filter options from services
        context['tags'] = get_tags_from_queryset(qs, limit=20)
        context['categories'] = get_categories_from_queryset(qs, limit=15)
        context['countries'] = get_countries_with_locations(qs)
        
        return context
```

### Pattern 2: Management Command
```python
# management/commands/update_location_data.py
from locations.services.location_geocoding import geocode_multiple_locations
from locations.services.location_distance import recalculate_all_distances

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Geocode locations without coordinates
        locations = Location.objects.filter(coord_lat__isnull=True)
        geo_stats = geocode_multiple_locations(locations)
        self.stdout.write(f"Geocoded: {geo_stats['success']}")
        
        # Calculate distances
        dist_stats = recalculate_all_distances()
        self.stdout.write(f"Calculated: {dist_stats['calculated']}")
```

### Pattern 3: Admin Action
```python
# admin.py
from locations.services.location_distance import calculate_distance_to_departure_center

@admin.action(description='Calculate distances')
def calculate_distances(modeladmin, request, queryset):
    for location in queryset:
        calculate_distance_to_departure_center(location, request=request)
    
    messages.success(request, f"Calculated distances for {queryset.count()} locations")

class LocationAdmin(admin.ModelAdmin):
    actions = [calculate_distances]
```

### Pattern 4: Signal Integration
```python
# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from locations.services.location_distance import calculate_distance_to_departure_center

@receiver(post_save, sender=Location)
def calculate_distance_on_save(sender, instance, created, **kwargs):
    """Auto-calculate distance when coordinates change."""
    if instance.coord_lat and instance.coord_lon:
        if not instance.distance_to_departure_center:
            calculate_distance_to_departure_center(instance)
```

---

## Testing Services

Services are tested separately from models:
```python
# tests/test_location_queries_service.py
from locations.services.location_queries import get_tags_from_queryset

def test_get_tags_respects_limit():
    for i in range(10):
        tag = TagFactory()
        loc = LocationFactory()
        loc.tags.add(tag)
    
    qs = Location.objects.all()
    tags = list(get_tags_from_queryset(qs, limit=5))
    
    assert len(tags) == 5
```

See [testing.md](testing.md) for comprehensive testing guide.

---

## Performance Optimization

### Query Optimization

All services use efficient queries:
```python
# ✅ Good - single query
tags = get_tags_from_queryset(queryset)

# ❌ Bad - N+1 queries
tags = {}
for location in queryset:
    for tag in location.tags.all():
        tags[tag.id] = tag
```

### Caching Strategy
```python
# Cache filter options for 5 minutes
from django.core.cache import cache

def get_cached_tags(queryset):
    cache_key = f'tags_{hash(queryset.query)}'
    tags = cache.get(cache_key)
    
    if tags is None:
        tags = list(get_tags_from_queryset(queryset))
        cache.set(cache_key, tags, 300)  # 5 minutes
    
    return tags
```

### Batch Processing

For large operations, process in batches:
```python
from django.db import transaction

def batch_calculate_distances(queryset, batch_size=100):
    total = queryset.count()
    
    for i in range(0, total, batch_size):
        batch = queryset[i:i+batch_size]
        
        with transaction.atomic():
            for location in batch:
                calculate_distance_to_departure_center(location)
        
        print(f"Processed {min(i+batch_size, total)}/{total}")
```

---

## Error Handling

All services handle errors gracefully:
```python
try:
    result = geocode_location(location, request=request)
except GeocoderQueryError as e:
    # Error logged and message added to request
    logger.error(f"Geocoding failed: {e}")
except Exception as e:
    # Unexpected errors
    logger.exception(f"Unexpected error: {e}")
```

Services never raise exceptions to views - they return `None` or empty results on failure.