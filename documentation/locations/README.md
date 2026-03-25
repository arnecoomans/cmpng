# Locations App Structure

## Overview

The `locations` app follows a **service-oriented architecture** where business logic is separated from models into dedicated service modules.

## Directory Structure
```
locations/
├── models/                    # Data models
│   ├── __init__.py
│   ├── Location.py           # Location, Description, Manager, QuerySet
│   ├── Region.py             # Geographic hierarchy
│   ├── Category.py           # Location categorization
│   ├── Tag.py                # Flexible tagging
│   ├── Chain.py              # Company/brand chains
│   └── Link.py               # External URLs
├── services/                  # Business logic layer
│   ├── __init__.py
│   ├── location_queries.py   # Query builders and aggregations
│   ├── location_geocoding.py # Google Maps geocoding
│   └── location_distance.py  # Distance calculations
├── views/                     # Request handlers
│   ├── __init__.py
│   └── locations/
│       ├── __init__.py
│       └── list.py           # Location list view
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── factories.py          # Factory Boy factories
│   ├── test_location_model.py
│   ├── test_region_model.py
│   └── test_location_queries_service.py
├── utils/                     # Utility functions
│   ├── __init__.py
│   └── geo.py                # Geocoding helpers
├── admin.py                   # Django admin configuration
└── urls.py                    # URL patterns
```

## Architecture Patterns

### Service Layer Pattern

Business logic lives in **services**, not models. Models remain focused on data structure and relationships.

**Model responsibilities:**
- Define fields and relationships
- Core data validation
- Simple property methods
- Delegate to services via thin wrappers

**Service responsibilities:**
- Complex queries and aggregations
- External API calls (Google Maps)
- Business calculations (distances)
- Batch operations

**Example:**
```python
# ❌ Don't put this in the model
class Location(models.Model):
    def geocode(self):
        geolocator = GoogleV3(api_key=settings.GOOGLE_API_KEY)
        result = geolocator.geocode(self.address)
        # ... 30 lines of logic ...

# ✅ Do this instead
class Location(models.Model):
    def geocode(self, request=None):
        """Geocode this location. Delegates to service."""
        from locations.services.location_geocoding import geocode_location
        return geocode_location(self, request=request)
```

### Custom Manager & QuerySet

Locations use a **custom manager** for optimized queries:
```python
# Basic queryset
Location.objects.all()

# Optimized queryset (with relations, annotations, ordering)
Location.objects.optimized()

# Chainable optimization methods
Location.objects.with_relations().with_distances()
```

### Filter Mapping

URL parameters map to database fields via `get_filter_mapping()`:
```
?country=nl        → region__parent__parent__slug=nl
?category=camping  → categories__slug=camping
?tag=pet-friendly  → tags__slug=pet-friendly
```

This allows clean URLs while maintaining complex database relationships.

## Data Flow

### Location List View Request Flow
```
1. User visits /locations/?country=nl&category=camping
2. LocationListView.get_queryset()
   ├─ Calls Location.get_optimized_queryset()
   │  └─ Returns queryset with relations, distances, ordering
   ├─ Applies filters via FilterMixin
   │  └─ Uses Location.get_filter_mapping() for URL params
   └─ Returns filtered queryset
3. LocationListView.get_context_data()
   ├─ Calls Location.get_tags_from_queryset()
   │  └─ Delegates to location_queries service
   ├─ Calls Location.get_categories_from_queryset()
   │  └─ Delegates to location_queries service
   └─ Returns context with locations + filter options
4. Template renders hierarchical list
```

### Distance Calculation Flow
```
1. Management command: python manage.py calculate_distances
2. For each location:
   ├─ location.calculate_distance_to_departure_center()
   │  └─ Delegates to location_distance service
   │     ├─ Calls get_departure_coordinates() utility
   │     ├─ Uses geopy.distance to calculate
   │     └─ Saves to location.distance_to_departure_center
   └─ region.calculate_average_distance_to_center()
      └─ Aggregates distances from child locations/regions
```

## Models

### Location

**Purpose**: Represents a physical location (accommodation or activity)

**Key Fields:**
- `name`, `slug` - Identification
- `coord_lat`, `coord_lon` - GPS coordinates
- `distance_to_departure_center` - Cached distance (km)
- `is_accommodation`, `is_activity` - Type flags (auto-calculated)

**Key Relationships:**
- `region` → Region (ForeignKey, SET_NULL)
- `categories` → Category (ManyToMany)
- `tags` → Tag (ManyToMany)
- `chain` → Chain (ForeignKey, SET_NULL)

**Type Detection:**
Types are automatically set based on category hierarchy. Categories with root name "Activity" set `is_activity=True`, others set `is_accommodation=True`. Both can be true.

### Region

**Purpose**: Hierarchical geographic structure

**Hierarchy Levels:**
1. **Country** (level='country', parent=None)
2. **Region** (level='region', parent=Country)
3. **Department** (level='department', parent=Region)
4. **Locality** (level='locality', parent=Department) - optional

**Key Fields:**
- `level` - Auto-calculated from hierarchy depth
- `cached_average_distance_to_center` - Cached average of child distances

**Self-referential:** `parent` → Region (CASCADE)

### Category

**Purpose**: Hierarchical categorization (Camping > Tent Camping > Glamping)

**Hierarchy:** Self-referential with `parent` field (CASCADE)

**Usage:** Determines location type via root category name

### Tag

**Purpose**: Flexible labeling with visibility control

**Features:**
- Hierarchical (self-referential parent)
- Visibility flags (inherited from VisibilityModel)
- Bidirectional slug/name generation

### Chain

**Purpose**: Company/brand hierarchy (Novotel → Accor → ParentCorp)

**Cascade:** `parent` uses SET_NULL (children become root chains)

## Services

### location_queries.py

**Functions:**
- `get_tags_from_queryset(queryset, limit, min_usage)`
- `get_categories_from_queryset(queryset, limit, min_usage)`
- `get_countries_with_locations(queryset)`
- `get_regions_with_locations(queryset)`
- `get_departments_with_locations(queryset)`

**Purpose:** Extract filter options from location querysets

**Usage:** Populate filter dropdowns in views

### location_geocoding.py

**Functions:**
- `geocode_location(location, request)`
- `geocode_multiple_locations(queryset, request)`

**Purpose:** Convert addresses to GPS coordinates using Google Maps API

**Dependencies:** `geopy`, `GOOGLE_API_KEY`

### location_distance.py

**Functions:**
- `calculate_distance_to_departure_center(location, request)`
- `recalculate_all_distances(queryset, request)`

**Purpose:** Calculate and cache distances from departure center

**Dependencies:** `geopy`, `DEPARTURE_CENTER` setting

## Utilities

### geo.py

**Function:** `get_departure_coordinates()`

**Purpose:** Geocode departure center with 30-day caching

**Returns:** `(latitude, longitude)` tuple

**Caching:** Uses Django cache to avoid repeated API calls

## Testing Strategy

See [testing.md](testing.md) for detailed testing documentation.

**Test Structure:**
- Model tests → Test data structure and relationships
- Delegation tests → Verify model correctly calls services (mocked)
- Service tests → Test actual business logic (real DB)

## Future Enhancements

- [ ] Add `Visits` model for tracking user visits
- [ ] Implement preferences system for departure center per user
- [ ] Add image management for locations
- [ ] Create API endpoints for mobile app
- [ ] Add search indexing (Elasticsearch/PostgreSQL full-text)