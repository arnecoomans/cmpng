# Working with Claude on CMPNG

This document helps Claude (and Claude Code) understand the CMPNG project structure, conventions, and best practices for effective collaboration.

## Project Overview

**Name:** CMPNG (cmpng)  
**Framework:** Django 5.1  
**Python:** 3.12+  
**Database:** SQLite
**Testing:** pytest + factory_boy  
**Purpose:** Vacation planning platform for managing accommodations and activities across Europe

## Quick Project Context

You are working on a Django application that helps users find and plan visits to camping locations, hotels, and activities. The app uses a hierarchical geographic structure (Country → Region → Department) and supports filtering by categories, tags, and distance from a home location.

## Project Structure
```
cmpng/
├── cmpng/                      # Project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── cmnsd/                      # Common/shared code (BaseModel, mixins, utilities)
│   ├── models/
│   │   ├── BaseModel.py       # Abstract base with token, status, dates, user
│   │   └── VisibilityModel.py # Abstract visibility control
│   ├── mixins/
│   │   ├── RequestMixin.py    # Request handling utilities
│   │   ├── FilterMixin.py     # FilterMixin for querysets
│   │   ├── MessagesMixin.py   # Django messages helpers
│   │   └── ResponseMixin.py   # Response utilities
│   └── admin.py               # BaseModelAdmin
├── locations/                  # Main app - locations, regions, categories, tags
│   ├── models/
│   │   ├── Location.py        # Main model: locations with coordinates & distances
│   │   ├── Region.py          # Geographic hierarchy
│   │   ├── Category.py        # Hierarchical categorization
│   │   ├── Tag.py             # Flexible labeling
│   │   ├── Chain.py           # Company/brand chains
│   │   ├── Link.py            # External URLs
│   │   └── Preferences.py     # UserPreferences & Visits models
│   ├── services/              # Business logic layer
│   │   ├── location_queries.py    # Query builders & aggregations
│   │   ├── location_geocoding.py  # Google Maps API integration
│   │   └── location_distance.py   # Distance calculations
│   ├── views/
│   │   └── locations/
│   │       └── locations_list.py  # LocationListMasterView, AllLocationListView,
│   │                              # AccommodationListView, ActivityListView
│   ├── tests/
│   │   ├── factories.py                        # Factory Boy factories
│   │   ├── conftest.py
│   │   ├── test_location_model.py
│   │   ├── test_location_queries_service.py
│   │   ├── test_location_list_view.py
│   │   ├── test_category_model.py
│   │   ├── test_chain_model.py
│   │   ├── test_description_model.py
│   │   ├── test_link_model.py
│   │   ├── test_region_model.py
│   │   └── test_tag_model.py
│   ├── management/commands/
│   │   ├── calculate_distances.py
│   │   └── create_fixture_users.py
│   ├── utils/
│   │   └── get_departure_coordinates.py
│   └── admin.py
├── documentation/              # Project documentation
│   ├── README.md
│   ├── CHANGELOG.md
│   └── locations/
│       ├── README.md
│       ├── structure.md       # Architecture & patterns
│       ├── testing.md         # Testing guide
│       ├── models.md          # Model reference
│       ├── services.md        # Service layer docs
│       └── api.md
└── manage.py
```

## Core Architectural Patterns

### 1. Service Layer Pattern

**Business logic lives in services, not models.**
```python
# ❌ Don't do this - business logic in model
class Location(models.Model):
    def geocode(self):
        geolocator = GoogleV3(api_key=settings.GOOGLE_API_KEY)
        # ... 30 lines of geocoding logic ...

# ✅ Do this - delegate to service
class Location(models.Model):
    def geocode(self, request=None):
        """Geocode this location. Delegates to service."""
        from locations.services.location_geocoding import geocode_location
        return geocode_location(self, request=request)
```

**Service responsibilities:**
- Complex queries and aggregations
- External API calls (Google Maps)
- Business calculations (distances)
- Batch operations

**Model responsibilities:**
- Define fields and relationships
- Core data validation
- Simple property methods
- Thin wrappers that delegate to services

### 2. Custom Manager & QuerySet

Use custom managers for optimized queries:
```python
class LocationQuerySet(models.QuerySet):
    def with_relations(self):
        return self.select_related('region__parent__parent').prefetch_related('tags')
    
    def with_distances(self):
        return self.annotate(country_distance=Coalesce(...))
    
    def optimized(self):
        return self.with_relations().with_distances().order_by(...)

class LocationManager(models.Manager):
    def get_queryset(self):
        return LocationQuerySet(self.model, using=self._db)
    
    def optimized(self):
        return self.get_queryset().optimized()

class Location(BaseModel):
    objects = LocationManager()
    
    @classmethod
    def get_optimized_queryset(cls):
        """Public API for getting optimized queryset."""
        return cls.objects.optimized()
```

### 3. Test-Driven Development

Write tests BEFORE implementing features:
```python
# 1. Write the test (RED)
def test_location_calculates_distance():
    location = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    distance = location.calculate_distance_to_departure_center()
    assert distance > 0

# 2. Implement the feature (GREEN)
def calculate_distance_to_departure_center(location, request=None):
    # ... implementation ...
    return distance

# 3. Refactor if needed (REFACTOR)
```

**Test structure:**
- Model tests → Data structure, relationships, core methods
- Service tests → Business logic in isolation
- Delegation tests → Models call services correctly (mocked)
- View tests → HTTP requests, context, templates

### 4. Factory Boy for Test Fixtures

Use factories instead of creating test data manually:
```python
# ❌ Don't do this
def test_something():
    user = User.objects.create(username='test', email='test@example.com')
    region = Region.objects.create(name='Test', slug='test')
    location = Location.objects.create(name='Test', region=region, user=user)

# ✅ Do this
def test_something():
    location = LocationFactory()  # All relationships handled automatically
```

### 5. Hierarchical Geographic Structure

**Always use the full 3-level hierarchy:**
```python
# Country (level 0, parent=None)
netherlands = RegionFactory(name='Netherlands', parent=None, level='country')

# Region (level 1, parent=Country)
utrecht = RegionFactory(name='Utrecht', parent=netherlands, level='region')

# Department (level 2, parent=Region)
bunnik = RegionFactory(name='Bunnik', parent=utrecht, level='department')

# Location (attached to department)
location = LocationFactory(region=bunnik)
```

**Filter mappings for clean URLs:**
```python
?country=nl        → region__parent__parent__slug=nl
?region_name=utrecht → region__parent__slug=utrecht
?department=bunnik  → region__slug=bunnik
```

## Code Conventions

### Indentation

Use **2-space indentation** (not 4 spaces) throughout all Python files.

```python
# ✅ Correct
class MyModel(models.Model):
  name = models.CharField(max_length=100)

  def __str__(self):
    return self.name

# ❌ Wrong
class MyModel(models.Model):
    name = models.CharField(max_length=100)
```

### Django Conventions
```python
# Model naming: Singular, PascalCase
class Location(models.Model):
    pass

# Manager naming: ModelNameManager
class LocationManager(models.Manager):
    pass

# QuerySet naming: ModelNameQuerySet
class LocationQuerySet(models.QuerySet):
    pass

# Factory naming: ModelNameFactory
class LocationFactory(DjangoModelFactory):
    pass

# Service files: lowercase with underscores
# locations/services/location_queries.py

# Test files: test_<what>_<type>.py
# test_location_model.py
# test_location_queries_service.py
```

### File Organization
```python
# Models: One model per file in models/ directory
locations/models/
├── __init__.py          # Import all models
├── Location.py          # Location + Description + Manager + QuerySet
├── Region.py
└── Category.py

# Services: Grouped by domain
locations/services/
├── __init__.py
├── location_queries.py     # Query builders
├── location_geocoding.py   # Google Maps integration
└── location_distance.py    # Distance calculations

# Views: Nested by model and view type
locations/views/
├── __init__.py
└── locations/
    ├── __init__.py
    ├── list.py        # LocationListView
    └── detail.py      # LocationDetailView (future)
```

### Import Order
```python
# 1. Standard library
from datetime import datetime
import logging

# 2. Django imports
from django.db import models
from django.conf import settings

# 3. Third-party imports
from geopy import distance
import pytest

# 4. Local app imports
from locations.models import Location
from locations.services.location_queries import get_tags_from_queryset

# 5. Relative imports (avoid when possible)
from .models import Region
```

### Docstring Style (Google Format)
```python
def get_tags_from_queryset(queryset, limit=20, min_usage=1):
    """
    Get unique tags from a location queryset, ordered by usage.
    
    Args:
        queryset: Location queryset to extract tags from
        limit: Maximum number of tags (None = unlimited)
        min_usage: Minimum locations that must use the tag
    
    Returns:
        QuerySet of dicts with id, slug, name, location_count
    
    Example:
        >>> tags = get_tags_from_queryset(qs, limit=10)
        >>> for tag in tags:
        ...     print(tag['name'])
    """
    # Implementation
```

## Important Model Details

### BaseModel (Abstract)

All models inherit from `BaseModel`:
```python
# Fields automatically available:
- token          # Unique public ID (10 chars, auto-generated)
- status         # 'c'=concept, 'p'=published, 'r'=revoked, 'x'=deleted
- date_created   # Auto timestamp
- date_modified  # Auto timestamp
- user           # ForeignKey to User (nullable)

# Methods:
- save()         # Auto-generates token if missing
- ajax_slug      # Property: "{id}-{slug}" or "{id}-{token}"
- get_model_fields()  # Class method: list of field names
```

### VisibilityModel (Abstract)

Models that need visibility control inherit from `VisibilityModel`:
```python
# Field:
- visibility     # 'p'=public, 'c'=community, 'f'=family, 'q'=private

# Default: 'c' (community)
```

### Location Type Detection

Location types are **auto-calculated** based on categories:
```python
# Type flags (not editable):
- is_accommodation  # Boolean
- is_activity       # Boolean

# Logic in _update_types():
# - No categories → is_accommodation=True
# - Category with root "Activity" → is_activity=True
# - Other categories → is_accommodation=True
# - Can have both flags True
```

**Important:** After adding categories, call `_update_types()`:
```python
location = LocationFactory()
location.categories.add(camping_category)
location._update_types()  # Recalculates flags
location.save()
```

### Distance Caching

Distances are **cached** in the database:
```python
# Location fields:
- distance_to_departure_center  # IntegerField (km), nullable

# Region fields:
- cached_average_distance_to_center  # FloatField (km), nullable

# Calculation triggers:
# 1. Manual: location.calculate_distance_to_departure_center()
# 2. Management command: python manage.py calculate_distances
# 3. Cascades to parent regions automatically
```

## Common Tasks

### Creating a New Location
```python
from locations.models import Location, Region, Category
from locations.services.location_geocoding import geocode_location
from locations.services.location_distance import calculate_distance_to_departure_center

# Create location
location = Location.objects.create(
    name='Camping Paradise',
    address='123 Main St, Amsterdam, Netherlands',
    status='p',
    visibility='p'
)

# Set region (must be department level)
amsterdam_dept = Region.objects.get(slug='amsterdam')
location.region = amsterdam_dept
location.save()

# Add categories
camping = Category.objects.get(slug='camping')
location.categories.add(camping)
location._update_types()
location.save()

# Geocode and calculate distance
geocode_location(location)
calculate_distance_to_departure_center(location)
```

### Getting Filter Options for a View
```python
from locations.services.location_queries import (
    get_tags_from_queryset,
    get_categories_from_queryset,
    get_countries_with_locations
)

# In view's get_context_data():
qs = self.get_queryset()

context['tags'] = get_tags_from_queryset(qs, limit=20, min_usage=2)
context['categories'] = get_categories_from_queryset(qs, limit=15)
context['countries'] = get_countries_with_locations(qs)
```

### Running Tests
```bash
# All tests
pytest

# Specific app
pytest locations/tests/ -v

# Specific file
pytest locations/tests/test_location_model.py -v

# Specific test
pytest locations/tests/test_location_model.py::TestLocationTypes::test_activity_flag -v

# With coverage
pytest --cov=locations --cov-report=html

# Watch mode (requires pytest-watch)
ptw locations/tests/
```

### Creating a New Service Function
```python
# 1. Create the service function
# locations/services/location_analytics.py
def get_location_statistics(queryset):
    """Calculate statistics for a location queryset."""
    return {
        'total': queryset.count(),
        'accommodations': queryset.filter(is_accommodation=True).count(),
        'activities': queryset.filter(is_activity=True).count(),
    }

# 2. Add delegation method to model (optional but recommended)
# locations/models/Location.py
class Location(BaseModel):
    @classmethod
    def get_statistics(cls, queryset):
        """Get statistics. Delegates to service."""
        from locations.services.location_analytics import get_location_statistics
        return get_location_statistics(queryset)

# 3. Write tests
# locations/tests/test_location_analytics_service.py
def test_get_statistics_counts_locations():
    LocationFactory.create_batch(5, is_accommodation=True)
    LocationFactory.create_batch(3, is_activity=True)
    
    qs = Location.objects.all()
    stats = get_location_statistics(qs)
    
    assert stats['total'] == 8
    assert stats['accommodations'] == 5
    assert stats['activities'] == 3

# 4. Use in views
stats = Location.get_statistics(queryset)
```

## Common Gotchas

### 1. Region Hierarchy Levels
```python
# ❌ Wrong - incomplete hierarchy
country = RegionFactory(level='country')
department = RegionFactory(level='department', parent=country)  # Missing region!

# ✅ Correct - full 3-level hierarchy
country = RegionFactory(level='country', parent=None)
region = RegionFactory(level='region', parent=country)
department = RegionFactory(level='department', parent=region)
```

### 2. Type Detection Not Automatic on Category Change
```python
# ❌ Wrong - type flags won't update
location.categories.add(activity_category)
assert location.is_activity  # FAILS! Still False

# ✅ Correct - manually trigger update
location.categories.add(activity_category)
location._update_types()
location.save()
location.refresh_from_db()
assert location.is_activity  # PASSES
```

### 3. Forgetting to Refresh from DB in Tests
```python
# ❌ Wrong - won't see saved changes
location.name = 'New Name'
location.save()
assert location.name == 'New Name'  # Uses in-memory value

# ✅ Correct - reload from database
location.name = 'New Name'
location.save()
location.refresh_from_db()
assert location.name == 'New Name'  # Uses DB value
```

### 4. N+1 Query Problems
```python
# ❌ Wrong - N+1 queries
locations = Location.objects.all()
for loc in locations:
    print(loc.region.name)  # Query per location!
    print(loc.categories.all())  # Query per location!

# ✅ Correct - single query with joins
locations = Location.objects.select_related('region').prefetch_related('categories')
for loc in locations:
    print(loc.region.name)
    print(loc.categories.all())

# ✅ Best - use optimized queryset
locations = Location.get_optimized_queryset()
```

### 5. Testing with Wrong Status/Visibility
```python
# ❌ Wrong - draft locations filtered out
location = LocationFactory(status='c')  # concept/draft
tags = get_tags_from_queryset(Location.objects.all())
# Won't include tags from draft locations!

# ✅ Correct - use published status
location = LocationFactory(status='p', visibility='p')
```

## Settings You Need to Know
```python
# settings.py

# Distance calculation
DEPARTURE_CENTER = 'Geldermalsen, Gelderland, Netherlands'

# Google Maps API
GOOGLE_API_KEY = env('GOOGLE_API_KEY')  # Required for geocoding

# Filter defaults
FILTER_TAG_LIMIT = 20           # Default tags in filter dropdowns
FILTER_TAG_MIN_USAGE = 1        # Minimum locations per tag
FILTER_CATEGORY_LIMIT = 20
FILTER_CATEGORY_MIN_USAGE = 1

# Pagination
ITEMS_PER_PAGE = 20

# Model defaults
DEFAULT_MODEL_STATUS = 'p'      # Default status for new models

# Search configuration
SEARCH_QUERY_CHARACTER = 'q'    # URL param for free-text search
SEARCH_EXCLUDE_CHARACTER = 'exclude'
SEARCH_BLOCKED_FIELDS = []      # Fields not searchable (in addition to 'password')
```

## External Dependencies

### geopy (Geocoding & Distance)
```python
from geopy.geocoders import GoogleV3
from geopy import distance

# Geocoding
geolocator = GoogleV3(api_key=settings.GOOGLE_API_KEY)
result = geolocator.geocode('Amsterdam, Netherlands')
# result.latitude, result.longitude

# Distance calculation
dist = distance.distance(
    (52.0, 5.0),      # Point A
    (52.3676, 4.9041)  # Point B
)
# dist.km, dist.miles
```

### Factory Boy (Testing)
```python
from factory.django import DjangoModelFactory
import factory

class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location
    
    name = factory.Sequence(lambda n: f'Location {n}')
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    status = 'p'
    visibility = 'p'
```

## Database Schema Notes

### Important Constraints

- `Location.slug` - UNIQUE
- `Location.token` - UNIQUE (auto-generated)
- `Region.slug` - UNIQUE
- All models have `status` and `date_created`/`date_modified`

### Cascade Behaviors
```python
# Location.region → Region: SET_NULL (location keeps existing if region deleted)
# Location.chain → Chain: SET_NULL
# Region.parent → Region: CASCADE (deleting country deletes all child regions)
# Category.parent → Category: CASCADE
# Tag.parent → Tag: CASCADE
# Chain.parent → Chain: SET_NULL (children become root chains)
# Description.location → Location: CASCADE
# Link.location → Location: CASCADE
```

## When to Ask for Clarification

Ask the human when:

1. **Architecture decisions** - Should this be in services or models?
2. **New models** - What fields and relationships are needed?
3. **External APIs** - Which API/service should we use?
4. **Business logic** - How should this feature behave?
5. **Performance concerns** - Is this query optimization acceptable?
6. **Breaking changes** - This will change existing behavior, OK?

Don't ask when:

1. Following established patterns in the codebase
2. Writing tests for existing features
3. Fixing obvious bugs
4. Adding documentation
5. Refactoring without changing behavior

## Documentation to Reference

When working on the project, refer to:

- **`documentation/locations/structure.md`** - Architecture & patterns
- **`documentation/locations/models.md`** - Complete model reference
- **`documentation/locations/services.md`** - Service layer documentation
- **`documentation/locations/testing.md`** - How to write tests

## Working with Claude Code

When using Claude Code in this project:

### For New Features
```bash
# 1. Start with tests
# Create test file or add to existing
claude code "Add tests for location search functionality"

# 2. Implement feature
claude code "Implement location search in services/location_queries.py"

# 3. Add view integration
claude code "Add search to LocationListView"

# 4. Update documentation
claude code "Document search feature in services.md"
```

### For Bug Fixes
```bash
# 1. Write failing test
claude code "Add test that reproduces the distance calculation bug"

# 2. Fix the bug
claude code "Fix distance calculation in services/location_distance.py"

# 3. Verify all tests pass
pytest locations/tests/ -v
```

### For Refactoring
```bash
# 1. Ensure tests exist and pass
pytest locations/tests/test_location_model.py -v

# 2. Refactor with confidence
claude code "Extract geocoding logic to service layer"

# 3. Verify tests still pass
pytest locations/tests/test_location_model.py -v
```

## Project-Specific Terminology

- **Departure Center** - User's home location (for distance calculations)
- **Region Hierarchy** - Country → Region → Department (→ Locality)
- **Type Flags** - `is_accommodation` / `is_activity` (auto-calculated from categories)
- **Filter Mapping** - URL parameter aliases (e.g., `?country=nl` → `region__parent__parent__slug=nl`)
- **Optimized Queryset** - Queryset with `select_related`, `prefetch_related`, annotations, and ordering
- **Service Layer** - Business logic separated from models (in `services/` directory)

## Quick Reference Commands
```bash
# Development server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Django shell
python manage.py shell

# Run all tests
pytest

# Run with coverage
pytest --cov=locations --cov-report=html

# Create superuser
python manage.py createsuperuser

# Calculate distances (custom command)
python manage.py calculate_distances

# Export fixtures
python manage.py export_fixtures

# Import fixtures
python manage.py import_fixtures
```

## Current State of the Project

**Completed:**
- ✅ All models (Location, Region, Category, Tag, Chain, Link, Description, UserPreferences, Visits, List, ListItem, Distance, Media, Comment, Size)
- ✅ Service layer (location_queries, location_geocoding, location_distance, list_distance)
- ✅ Custom managers and querysets
- ✅ FilterMixin for complex filtering
- ✅ Auth system (login, logout, register, profile) via cmnsd
- ✅ Comprehensive test suite (536+ tests)

**Views — done:**
- ✅ Location views (list, detail, map) — to do: add location form, geocoding UI
- ✅ Tag views (TagListView)
- ✅ Comment views (CommentListView + per-location management)
- ✅ Visit views (ManageVisitsView — mark visited/unvisited)
- ✅ List views (ListListView, ListDetailView, ManageListsView) — to do: manage list metadata (name, template, visibility)
- ✅ Preferences view (UserPreferences + maps consent) — mostly done

**Upcoming:**
- ⏳ Add location form (create/edit with geocoding)
- ⏳ API endpoints
- ⏳ Media management UI

## Example Session

Here's how a typical Claude Code session might look:
```
Human: I need to add a feature where users can mark locations as favorites

Claude: I'll help you add favorites functionality. Let's follow the TDD approach:

1. First, let's create the model and tests
2. Then implement the service layer
3. Finally add view integration

Let me start by creating a Favorite model...

[Creates locations/models/Favorite.py with tests]
[Creates locations/services/location_favorites.py]
[Updates LocationListView to show favorite status]
[Updates documentation]

All tests pass! The favorites feature is ready.
```

---

## Summary

This is a well-structured Django project following modern best practices:

- **Service layer pattern** for business logic
- **Test-driven development** with pytest
- **Factory Boy** for test fixtures
- **Custom managers** for optimized queries
- **Comprehensive documentation**

When in doubt, follow the existing patterns in the codebase and refer to the documentation in `documentation/locations/`.

Happy coding! 🚀