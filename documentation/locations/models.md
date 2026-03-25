# Models Reference - Locations App

Complete reference for all models in the locations app.

## Table of Contents

- [Location](#location)
- [Description](#description)
- [Region](#region)
- [Category](#category)
- [Tag](#tag)
- [Chain](#chain)
- [Link](#link)

---

## Location

**File:** `locations/models/Location.py`

The primary model representing a physical location (accommodation or activity).

### Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `slug` | SlugField | URL-friendly identifier | Unique, max 255 chars |
| `name` | CharField | Location name | Required, max 255 chars |
| `summary` | CharField | Brief description | Optional, max 500 chars |
| `address` | CharField | Physical address | Optional, max 255 chars |
| `email` | EmailField | Contact email | Optional |
| `phone` | CharField | Contact phone | Optional, max 20 chars |
| `owners_name` | CharField | Owner/manager name | Optional, max 255 chars |
| `coord_lat` | FloatField | Latitude coordinate | Optional |
| `coord_lon` | FloatField | Longitude coordinate | Optional |
| `is_accommodation` | BooleanField | Accommodation flag | Auto-calculated, not editable |
| `is_activity` | BooleanField | Activity flag | Auto-calculated, not editable |
| `distance_to_departure_center` | IntegerField | Distance in km | Optional, cached value |

### Relationships

| Field | Type | Related Model | On Delete | Description |
|-------|------|---------------|-----------|-------------|
| `region` | ForeignKey | Region | SET_NULL | Geographic location |
| `categories` | ManyToMany | Category | - | Location categorization |
| `tags` | ManyToMany | Tag | - | Flexible labeling |
| `chain` | ForeignKey | Chain | SET_NULL | Company/brand chain |
| `visitors` | ManyToMany | User | Through Visits | Users who visited |

### Inherited Fields (from BaseModel)

- `token` - Unique public ID (auto-generated)
- `status` - Publication status ('c', 'p', 'r', 'x')
- `date_created` - Creation timestamp
- `date_modified` - Last modification timestamp
- `user` - Creator (ForeignKey to User, SET_NULL)

### Inherited Fields (from VisibilityModel)

- `visibility` - Who can see ('p'=public, 'c'=community, 'f'=family, 'q'=private)

### Meta
```python
class Meta:
    ordering = ['name']
```

### Manager & QuerySet

**Manager:** `LocationManager`

**QuerySet Methods:**
```python
# Get queryset with optimized joins
Location.objects.with_relations()

# Add distance annotations
Location.objects.with_distances()

# Apply default ordering
Location.objects.with_default_ordering()

# All optimizations in one call
Location.objects.optimized()
```

### Instance Methods

#### `save(*args, **kwargs)`

Overrides default save to:
1. Generate slug from name if not provided
2. Call `_update_types()` after M2M relationships exist
3. Save type flags
```python
location = Location(name='Camping Paradise')
location.save()  # slug auto-generated as 'camping-paradise'
```

#### `_update_types()`

**Internal method** - Recalculates `is_accommodation` and `is_activity` flags based on category hierarchy.

Logic:
- No categories → `is_accommodation=True`, `is_activity=False`
- Category with root "Activity" → `is_activity=True`
- Other categories → `is_accommodation=True`
- Can have both flags True

Called automatically in `save()`.

#### `geocode(request=None)`

Geocode the location's address using Google Maps API.

**Delegates to:** `locations.services.location_geocoding.geocode_location()`

**Returns:** `(latitude, longitude)` tuple or `None`
```python
location = Location.objects.get(slug='camping-paradise')
coords = location.geocode()
# Updates location.coord_lat and location.coord_lon
```

#### `calculate_distance_to_departure_center(request=None)`

Calculate and cache distance from departure center.

**Delegates to:** `locations.services.location_distance.calculate_distance_to_departure_center()`

**Returns:** Distance in km (int) or `None`

**Side effects:**
- Updates `location.distance_to_departure_center`
- Triggers `region.calculate_average_distance_to_center()` if changed
```python
distance = location.calculate_distance_to_departure_center()
print(f"Distance: {distance} km")
```

### Properties

#### `type`

Returns human-readable type string.

**Returns:** `'activity'`, `'accommodation'`, or `'mixed'`
```python
if location.type == 'activity':
    print("This is an activity location")
```

#### `country`

Returns the country name (top-level region).

**Returns:** Country name (str) or `None`
```python
print(f"Located in: {location.country}")
# Output: "Located in: Netherlands"
```

#### `region_name`

Returns the region name (middle level).

**Returns:** Region name (str) or `None`
```python
print(f"Region: {location.region_name}")
# Output: "Region: Utrecht"
```

#### `department`

Returns the department name (location's direct region).

**Returns:** Department name (str) or `None`
```python
print(f"Department: {location.department}")
# Output: "Department: Bunnik"
```

### Class Methods

#### `get_optimized_queryset()`

Returns a queryset with all optimizations applied.

**Returns:** Optimized LocationQuerySet

**Includes:**
- `select_related('region', 'region__parent', 'region__parent__parent')`
- `prefetch_related('categories', 'tags')`
- Distance annotations
- Default ordering
```python
locations = Location.get_optimized_queryset()
# Efficient query with all joins and annotations
```

#### `get_filter_mapping()`

Returns URL parameter aliases for filtering.

**Returns:** Dict mapping parameter names to field lookups
```python
mapping = Location.get_filter_mapping()
# {
#     'country': 'region__parent__parent__slug',
#     'category': 'categories__slug',
#     'tag': 'tags__slug',
# }
```

#### `get_tags_from_queryset(queryset, limit=20, min_usage=1)`

Get unique tags from a location queryset.

**Delegates to:** `locations.services.location_queries.get_tags_from_queryset()`

**Args:**
- `queryset` - Location queryset to extract tags from
- `limit` - Maximum number of tags (None = unlimited)
- `min_usage` - Minimum locations that must use the tag

**Returns:** QuerySet of dicts with `id`, `slug`, `name`, `location_count`
```python
qs = Location.objects.filter(country='nl')
tags = Location.get_tags_from_queryset(qs, limit=10, min_usage=2)

for tag in tags:
    print(f"{tag['name']}: {tag['location_count']} locations")
```

#### `get_categories_from_queryset(queryset, limit=20, min_usage=1)`

Get unique categories from a location queryset.

**Delegates to:** `locations.services.location_queries.get_categories_from_queryset()`

**Args:** Same as `get_tags_from_queryset()`

**Returns:** QuerySet of dicts with `id`, `slug`, `name`, `location_count`
```python
categories = Location.get_categories_from_queryset(qs)
```

#### `get_countries_with_locations(queryset=None)`

Get all countries that have locations.

**Delegates to:** `locations.services.location_queries.get_countries_with_locations()`

**Args:**
- `queryset` - Location queryset (default: all locations)

**Returns:** QuerySet of dicts with country info
```python
countries = Location.get_countries_with_locations()

for country in countries:
    print(country['region__parent__parent__name'])
```

#### `get_regions_with_locations(queryset=None)`

Get all regions that have locations.

**Delegates to:** `locations.services.location_queries.get_regions_with_locations()`
```python
regions = Location.get_regions_with_locations()
```

#### `get_departments_with_locations(queryset=None)`

Get all departments that have locations.

**Delegates to:** `locations.services.location_queries.get_departments_with_locations()`
```python
departments = Location.get_departments_with_locations()
```

### Usage Examples

#### Creating a Location
```python
# Create with minimal info
location = Location.objects.create(
    name='Camping Paradise',
    status='p',
    visibility='p'
)

# Add address and geocode
location.address = '123 Main St, Amsterdam, Netherlands'
location.save()
location.geocode()

# Add relationships
location.region = Region.objects.get(slug='amsterdam')
location.categories.add(Category.objects.get(slug='camping'))
location.tags.add(Tag.objects.get(slug='pet-friendly'))
location.save()

# Calculate distance
location.calculate_distance_to_departure_center()
```

#### Querying Locations
```python
# Get all published locations
locations = Location.objects.filter(status='p')

# Get optimized queryset
locations = Location.get_optimized_queryset()

# Filter by country
dutch_locations = locations.filter(region__parent__parent__slug='nl')

# Filter by type
activities = Location.objects.filter(is_activity=True)
accommodations = Location.objects.filter(is_accommodation=True)

# Filter by distance (requires distance to be calculated)
nearby = Location.objects.filter(
    distance_to_departure_center__lte=100
).order_by('distance_to_departure_center')
```

#### Working with Categories and Tags
```python
# Get locations by category
camping_locations = Location.objects.filter(categories__slug='camping')

# Get locations by multiple tags
pet_wifi_locations = Location.objects.filter(
    tags__slug__in=['pet-friendly', 'wifi']
).distinct()

# Get filter options for current queryset
qs = Location.objects.filter(region__parent__parent__slug='nl')
available_tags = Location.get_tags_from_queryset(qs, limit=20)
available_categories = Location.get_categories_from_queryset(qs)
```

---

## Description

**File:** `locations/models/Location.py`

Additional text descriptions for locations (supports Markdown).

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | TextField | Markdown-formatted description |
| `location` | ForeignKey | Parent location (CASCADE) |

### Relationships

- `location` → Location (CASCADE)
- Inherits from BaseModel and VisibilityModel

### Usage
```python
# Add description to location
description = Description.objects.create(
    location=location,
    description='# Welcome\n\nThis is a great camping spot...',
    status='p',
    visibility='p'
)

# Access from location
for desc in location.descriptions.all():
    print(desc.description)
```

---

## Region

**File:** `locations/models/Region.py`

Hierarchical geographic structure (Country → Region → Department → Locality).

### Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `name` | CharField | Region name | Required, max 255 chars |
| `slug` | SlugField | URL identifier | Unique, max 255 chars |
| `level` | CharField | Hierarchy level | Auto-calculated |
| `coord_lat` | FloatField | Center latitude | Optional |
| `coord_lon` | FloatField | Center longitude | Optional |
| `cached_average_distance_to_center` | FloatField | Average child distance | Optional, cached |

### Relationships

| Field | Type | Related Model | On Delete | Description |
|-------|------|---------------|-----------|-------------|
| `parent` | ForeignKey | Region (self) | CASCADE | Parent region |

### Reverse Relationships

- `children` - Child regions (via `parent`)
- `locations` - Locations in this region

### Hierarchy Levels

1. **Country** - Top level (parent=None)
2. **Region** - Second level
3. **Department** - Third level
4. **Locality** - Fourth level (optional)

### Methods

#### `calculate_average_distance_to_center()`

Calculates average distance of all child locations and regions, then recursively updates parent.

**Side effects:** Updates `cached_average_distance_to_center` for self and ancestors
```python
region = Region.objects.get(slug='utrecht')
region.calculate_average_distance_to_center()
```

### Usage Examples
```python
# Create hierarchy
netherlands = Region.objects.create(
    name='Netherlands',
    slug='netherlands',
    level='country'
)

utrecht = Region.objects.create(
    name='Utrecht',
    slug='utrecht',
    parent=netherlands,
    level='region'
)

bunnik = Region.objects.create(
    name='Bunnik',
    slug='bunnik',
    parent=utrecht,
    level='department'
)

# Query hierarchy
all_dutch_regions = Region.objects.filter(parent__slug='netherlands')
all_utrecht_departments = Region.objects.filter(parent__slug='utrecht')

# Get all locations in a country (through hierarchy)
dutch_locations = Location.objects.filter(
    region__parent__parent__slug='netherlands'
)
```

---

## Category

**File:** `locations/models/Category.py`

Hierarchical categorization for locations.

### Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `name` | CharField | Category name | Required, max 255 chars |
| `slug` | SlugField | URL identifier | Unique, max 255 chars |
| `description` | TextField | Category description | Optional |

### Relationships

| Field | Type | Related Model | On Delete |
|-------|------|---------------|-----------|
| `parent` | ForeignKey | Category (self) | CASCADE |

### Reverse Relationships

- `children` - Subcategories (via `parent`)
- `locations` - Locations using this category

### Special Root Categories

- **"Activity"** - Root category that sets `is_activity=True` on locations
- **Other roots** - Set `is_accommodation=True` on locations

### Usage Examples
```python
# Create category hierarchy
accommodation = Category.objects.create(name='Accommodation', slug='accommodation')
camping = Category.objects.create(name='Camping', parent=accommodation, slug='camping')
glamping = Category.objects.create(name='Glamping', parent=camping, slug='glamping')

# Create activity hierarchy
activity = Category.objects.create(name='Activity', slug='activity')
beach = Category.objects.create(name='Beach', parent=activity, slug='beach')

# Assign to location
location.categories.add(glamping)
location._update_types()  # Sets is_accommodation=True

activity_location.categories.add(beach)
activity_location._update_types()  # Sets is_activity=True
```

---

## Tag

**File:** `locations/models/Tag.py`

Flexible labeling system for locations (hierarchical with visibility control).

### Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `name` | CharField | Tag name | Required, max 255 chars |
| `slug` | SlugField | URL identifier | Unique, max 255 chars |
| `description` | TextField | Tag description | Optional |

### Relationships

| Field | Type | Related Model | On Delete |
|-------|------|---------------|-----------|
| `parent` | ForeignKey | Tag (self) | CASCADE |

### Reverse Relationships

- `children` - Child tags (via `parent`)
- `locations` - Locations using this tag

### Features

- Hierarchical (self-referential parent)
- Visibility-controlled (inherited from VisibilityModel)
- Bidirectional slug/name generation

### Usage Examples
```python
# Create tags
pet_friendly = Tag.objects.create(name='Pet Friendly', slug='pet-friendly')
wifi = Tag.objects.create(name='WiFi', slug='wifi')
pool = Tag.objects.create(name='Swimming Pool', slug='swimming-pool')

# Create tag hierarchy
facilities = Tag.objects.create(name='Facilities', slug='facilities')
indoor_pool = Tag.objects.create(
    name='Indoor Pool',
    parent=facilities,
    slug='indoor-pool'
)

# Assign to location
location.tags.add(pet_friendly, wifi, pool)

# Query by tag
pet_locations = Location.objects.filter(tags__slug='pet-friendly')
```

---

## Chain

**File:** `locations/models/Chain.py`

Company/brand hierarchy for managing location chains.

### Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `name` | CharField | Chain name | Required, max 255 chars |
| `slug` | SlugField | URL identifier | Unique, max 255 chars |
| `description` | TextField | Chain description | Optional |

### Relationships

| Field | Type | Related Model | On Delete |
|-------|------|---------------|-----------|
| `parent` | ForeignKey | Chain (self) | SET_NULL |

**Note:** Uses SET_NULL (not CASCADE) so child chains become independent if parent is deleted.

### Reverse Relationships

- `children` - Child chains (via `parent`)
- `locations` - Locations belonging to this chain

### Usage Examples
```python
# Create chain hierarchy
accor = Chain.objects.create(name='Accor', slug='accor')
novotel = Chain.objects.create(name='Novotel', parent=accor, slug='novotel')
ibis = Chain.objects.create(name='Ibis', parent=accor, slug='ibis')

# Assign to location
location.chain = novotel
location.save()

# Query by chain
accor_locations = Location.objects.filter(
    Q(chain__slug='accor') | Q(chain__parent__slug='accor')
)
```

---

## Link

**File:** `locations/models/Link.py`

External URLs associated with locations.

### Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `url` | URLField | External URL | Required |
| `title` | CharField | Link title | Optional, max 255 chars |
| `description` | TextField | Link description | Optional |
| `location` | ForeignKey | Parent location | CASCADE |

### Relationships

- `location` → Location (CASCADE)

### Usage Examples
```python
# Add links to location
Link.objects.create(
    location=location,
    url='https://example.com',
    title='Official Website',
    status='p'
)

Link.objects.create(
    location=location,
    url='https://booking.com/...',
    title='Book Now',
    status='p'
)

# Access from location
for link in location.links.all():
    print(f"{link.title}: {link.url}")
```

---

## Model Inheritance Hierarchy
```
BaseModel (abstract)
├─ token, status, dates, user
└─ VisibilityModel (abstract)
   ├─ visibility
   └─ Location
      ├─ All BaseModel fields
      ├─ All VisibilityModel fields
      └─ Location-specific fields

BaseModel (abstract)
├─ Description (+ VisibilityModel)
├─ Region
├─ Category
├─ Tag (+ VisibilityModel)
├─ Chain
└─ Link
```

## Common Queries Across Models

### Get Published Items
```python
# Works for all models with status field
published_locations = Location.objects.filter(status='p')
published_regions = Region.objects.filter(status='p')
published_categories = Category.objects.filter(status='p')
```

### Get Public Visible Items
```python
# Works for models with visibility field
public_locations = Location.objects.filter(visibility='p')
public_tags = Tag.objects.filter(visibility='p')
```

### Get Items by User
```python
# Works for all models with user field
my_locations = Location.objects.filter(user=request.user)
my_regions = Region.objects.filter(user=request.user)
```

### Hierarchical Queries
```python
# Get all descendants
def get_descendants(model_instance):
    """Get all descendants of a hierarchical model (Region, Category, Tag, Chain)"""
    descendants = []
    for child in model_instance.children.all():
        descendants.append(child)
        descendants.extend(get_descendants(child))
    return descendants

# Get root item
def get_root(model_instance):
    """Get root ancestor"""
    item = model_instance
    while item.parent:
        item = item.parent
    return item
```