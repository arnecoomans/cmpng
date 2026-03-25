# Testing Guide - Locations App

## Overview

The locations app uses **pytest** with **factory_boy** for fixture generation. Tests are organized by concern: model tests, service tests, and view tests.

## Test Structure
```
locations/tests/
├── __init__.py
├── conftest.py                        # Shared fixtures
├── factories.py                       # Factory Boy factories
├── test_location_model.py            # Location model tests
├── test_region_model.py              # Region model tests
├── test_category_model.py            # Category model tests
├── test_tag_model.py                 # Tag model tests
├── test_chain_model.py               # Chain model tests
├── test_link_model.py                # Link model tests
├── test_description_model.py         # Description model tests
├── test_location_queries_service.py  # Query service tests
└── test_location_list_view.py        # View tests
```

## Running Tests
```bash
# Run all location tests
pytest locations/tests/ -v

# Run specific test file
pytest locations/tests/test_location_model.py -v

# Run specific test class
pytest locations/tests/test_location_model.py::TestLocationTypes -v

# Run specific test
pytest locations/tests/test_location_model.py::TestLocationTypes::test_activity_category_sets_is_activity_flag -v

# Run with coverage
pytest locations/tests/ --cov=locations --cov-report=html

# Run tests matching a pattern
pytest locations/tests/ -k "test_slug" -v
```

## Test Categories

### 1. Model Tests

**Purpose:** Test data structure, validation, relationships, and model methods

**Location:** `test_*_model.py` files

**What to test:**
- Field validation (required, optional, constraints)
- String representation (`__str__`)
- Slug generation
- Default values
- Relationships (ForeignKey, ManyToMany)
- Model methods (save, custom methods)
- Properties

**Example:**
```python
@pytest.mark.django_db
class TestLocationSlug:
    
    def test_slug_auto_generated_from_name(self, db):
        location = LocationFactory(name='Central Park', slug='')
        assert location.slug == slugify('Central Park')
    
    def test_slug_not_overwritten_if_provided(self, db):
        location = LocationFactory(name='Central Park', slug='my-custom-slug')
        assert location.slug == 'my-custom-slug'
```

**Coverage target:** 90%+

### 2. Service Tests

**Purpose:** Test business logic in isolation

**Location:** `test_*_service.py` files

**What to test:**
- Query building and filtering
- Aggregations and calculations
- External API interactions (mocked when appropriate)
- Edge cases and error handling
- Return value structure

**Example:**
```python
@pytest.mark.django_db
class TestGetTagsFromQueryset:
    
    def test_returns_tags_from_queryset(self):
        tag = TagFactory(name='Pet Friendly')
        loc = LocationFactory()
        loc.tags.add(tag)
        
        qs = Location.objects.all()
        tags = get_tags_from_queryset(qs)
        
        tag_ids = [t['id'] for t in tags]
        assert tag.id in tag_ids
    
    def test_respects_limit_parameter(self):
        for i in range(10):
            tag = TagFactory(name=f'Tag {i}')
            loc = LocationFactory()
            loc.tags.add(tag)
        
        qs = Location.objects.all()
        tags = list(get_tags_from_queryset(qs, limit=5))
        
        assert len(tags) == 5
```

**Coverage target:** 95%+

### 3. Delegation Tests

**Purpose:** Verify models correctly delegate to services

**Location:** Within model test files (e.g., `TestLocationServiceDelegation` class)

**What to test:**
- Model methods call the correct service function
- Correct parameters are passed
- Return values are propagated

**Example:**
```python
class TestLocationServiceDelegation:
    
    def test_get_tags_from_queryset_delegates_to_service(self, db):
        from unittest.mock import patch
        
        qs = Location.objects.all()
        
        with patch('locations.services.location_queries.get_tags_from_queryset') as mock:
            mock.return_value = []
            result = Location.get_tags_from_queryset(qs, limit=10)
            mock.assert_called_once_with(qs, limit=10, min_usage=1)
```

**Coverage target:** 100% (these are simple)

### 4. View Tests

**Purpose:** Test HTTP request/response and view logic

**Location:** `test_*_view.py` files

**What to test:**
- Status codes
- Template usage
- Context data
- Query parameter handling
- Permissions
- Form handling (future)

**Example:**
```python
@pytest.mark.django_db
class TestLocationListView:
    
    def test_location_list_view_exists(self, client):
        url = reverse('locations:home')
        response = client.get(url)
        assert response.status_code == 200
    
    def test_filter_by_country(self, client):
        nl = RegionFactory(name='Netherlands', level='country')
        # ... create hierarchy and locations ...
        
        url = reverse('locations:home') + f'?country={nl.slug}'
        response = client.get(url)
        
        assert 'Dutch Location' in response.content.decode()
        assert 'Belgian Location' not in response.content.decode()
```

**Coverage target:** 85%+

## Test Fixtures

### Factory Boy Factories

Located in `locations/tests/factories.py`

**Available factories:**
- `UserFactory` - Creates users
- `RegionFactory` - Creates regions
- `CategoryFactory` - Creates categories
- `TagFactory` - Creates tags
- `ChainFactory` - Creates chains
- `LinkFactory` - Creates links
- `DescriptionFactory` - Creates descriptions
- `LocationFactory` - Creates locations

**Usage:**
```python
# Basic creation
location = LocationFactory()

# With overrides
location = LocationFactory(
    name='My Location',
    slug='my-location',
    status='p'
)

# With relationships
region = RegionFactory()
location = LocationFactory(region=region)

# Create without saving (for validation tests)
location = LocationFactory.build(name='')
```

### pytest Fixtures

Located in test files and `conftest.py`

**Common fixtures:**
```python
@pytest.fixture
def location(db):
    """A basic location."""
    return LocationFactory()

@pytest.fixture
def activity_category(db):
    """Root 'Activity' category."""
    return CategoryFactory(name='Activity', parent=None)

@pytest.fixture
def user(db):
    """A basic user."""
    return UserFactory()
```

**Usage:**
```python
def test_something(location, activity_category):
    location.categories.add(activity_category)
    # ... test logic
```

## Testing Patterns

### Testing Type Detection
```python
def test_activity_category_sets_is_activity_flag(db, activity_category):
    location = LocationFactory()
    location.categories.add(activity_category)
    location._update_types()
    location.save()
    location.refresh_from_db()
    
    assert location.is_activity is True
```

**Key steps:**
1. Create location
2. Add category
3. Call `_update_types()` (normally called in save)
4. Save and refresh
5. Assert flags

### Testing Hierarchical Queries
```python
def test_get_countries_returns_unique(db):
    # Create full hierarchy
    nl = RegionFactory(name='Netherlands', parent=None, level='country')
    utrecht = RegionFactory(name='Utrecht', parent=nl, level='region')
    amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')
    
    # Create multiple locations in same country
    LocationFactory(region=amsterdam)
    LocationFactory(region=amsterdam)
    
    qs = Location.objects.all()
    countries = list(get_countries_with_locations(qs))
    
    # Should return only one country despite multiple locations
    assert len(countries) == 1
    assert countries[0]['region__parent__parent__name'] == 'Netherlands'
```

### Testing Service Functions
```python
def test_service_orders_by_usage_count(db):
    tag_popular = TagFactory()
    tag_rare = TagFactory()
    
    # Setup data
    for _ in range(3):
        loc = LocationFactory()
        loc.tags.add(tag_popular)
    
    loc = LocationFactory()
    loc.tags.add(tag_rare)
    
    # Call service
    qs = Location.objects.all()
    tags = list(get_tags_from_queryset(qs))
    
    # Verify ordering
    assert tags[0]['id'] == tag_popular.id
    assert tags[0]['location_count'] == 3
```

### Mocking External APIs
```python
def test_geocode_calls_google_api(db, location):
    from unittest.mock import patch, Mock
    
    mock_result = Mock()
    mock_result.latitude = 52.0
    mock_result.longitude = 5.0
    
    with patch('geopy.geocoders.GoogleV3') as mock_geocoder:
        mock_geocoder.return_value.geocode.return_value = mock_result
        
        result = location.geocode()
        
        assert result == (52.0, 5.0)
        assert location.coord_lat == 52.0
        assert location.coord_lon == 5.0
```

## Common Pitfalls

### 1. Forgetting to refresh from DB
```python
# ❌ Wrong - won't see saved changes
location.save()
assert location.is_activity is True

# ✅ Correct - refreshes from database
location.save()
location.refresh_from_db()
assert location.is_activity is True
```

### 2. Not calling _update_types()
```python
# ❌ Wrong - type flags won't update
location.categories.add(activity_category)
assert location.is_activity is True  # FAILS

# ✅ Correct - manually trigger type calculation
location.categories.add(activity_category)
location._update_types()
location.save()
location.refresh_from_db()
assert location.is_activity is True  # PASSES
```

### 3. Creating incomplete hierarchies
```python
# ❌ Wrong - missing intermediate levels
country = RegionFactory(level='country')
department = RegionFactory(level='department', parent=country)
# Missing region level!

# ✅ Correct - complete hierarchy
country = RegionFactory(level='country', parent=None)
region = RegionFactory(level='region', parent=country)
department = RegionFactory(level='department', parent=region)
```

### 4. Testing with wrong status/visibility
```python
# ❌ Wrong - will be filtered out by queries
location = LocationFactory(status='c')  # Draft
tags = get_tags_from_queryset(Location.objects.all())
# Won't include tags from draft locations

# ✅ Correct - use published status
location = LocationFactory(status='p', visibility='p')
```

## Continuous Integration

Tests run automatically on:
- Every commit (pre-commit hook)
- Every pull request (GitHub Actions)
- Before deployment

**Required:** All tests must pass before merging to `main`.

## Writing New Tests

### Checklist for New Model Tests

- [ ] Test required fields raise validation errors
- [ ] Test optional fields accept None
- [ ] Test default values
- [ ] Test string representation
- [ ] Test all relationships (forward and reverse)
- [ ] Test custom model methods
- [ ] Test properties
- [ ] Test save() behavior
- [ ] Test unique constraints
- [ ] Test CASCADE/SET_NULL behavior

### Checklist for New Service Tests

- [ ] Test basic functionality (happy path)
- [ ] Test with empty queryset
- [ ] Test parameter handling (limit, filters)
- [ ] Test edge cases (None values, invalid data)
- [ ] Test return value structure
- [ ] Test with various querysets (filtered, unfiltered)
- [ ] Mock external dependencies (APIs)

## Test Data Guidelines

- Use factories for all test data creation
- Keep test data minimal (only what's needed for the test)
- Use descriptive names (`tag_popular`, not `tag1`)
- Clean up is automatic (pytest-django handles DB rollback)

## Coverage Goals

- **Models:** 90%+
- **Services:** 95%+
- **Views:** 85%+
- **Overall:** 90%+

Check coverage:
```bash
pytest --cov=locations --cov-report=html
open htmlcov/index.html
```