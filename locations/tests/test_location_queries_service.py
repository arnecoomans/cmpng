import pytest
from django.db.models import Count

from locations.models import Location, Tag, Category, Region
from locations.tests.factories import LocationFactory, TagFactory, CategoryFactory, RegionFactory, SizeFactory
from locations.services.location_queries import (
    get_tags_from_queryset,
    get_categories_from_queryset,
    get_countries_with_locations,
    get_regions_with_locations,
    get_departments_with_locations,
)


# ------------------------------------------------------------------ #
#  get_tags_from_queryset
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetTagsFromQueryset:
    
    def test_returns_tags_from_queryset(self):
        """Returns tags used by locations in queryset."""
        tag1 = TagFactory(name='Pet Friendly')
        tag2 = TagFactory(name='Family Friendly')
        tag3 = TagFactory(name='Wifi')
        
        loc1 = LocationFactory()
        loc1.tags.add(tag1, tag2)
        
        loc2 = LocationFactory()
        loc2.tags.add(tag2, tag3)
        
        qs = Location.objects.filter(id__in=[loc1.id, loc2.id])
        tags = get_tags_from_queryset(qs)
        
        tag_ids = [t['id'] for t in tags]
        assert tag1.id in tag_ids
        assert tag2.id in tag_ids
        assert tag3.id in tag_ids
    
    def test_excludes_tags_not_in_queryset(self):
        """Doesn't return tags from locations not in queryset."""
        tag1 = TagFactory(name='In Queryset')
        tag2 = TagFactory(name='Not In Queryset')
        
        loc1 = LocationFactory()
        loc1.tags.add(tag1)
        
        loc2 = LocationFactory()
        loc2.tags.add(tag2)
        
        qs = Location.objects.filter(id=loc1.id)
        tags = get_tags_from_queryset(qs)
        
        tag_ids = [t['id'] for t in tags]
        assert tag1.id in tag_ids
        assert tag2.id not in tag_ids
    
    def test_returns_distinct_tags(self):
        """Doesn't duplicate tags used by multiple locations."""
        tag = TagFactory(name='Popular Tag')
        
        loc1 = LocationFactory()
        loc1.tags.add(tag)
        
        loc2 = LocationFactory()
        loc2.tags.add(tag)
        
        qs = Location.objects.all()
        tags = list(get_tags_from_queryset(qs))
        
        # Should only appear once despite being on 2 locations
        assert len([t for t in tags if t['id'] == tag.id]) == 1
    
    def test_orders_by_usage_count_descending(self):
        """Most-used tags appear first."""
        tag_popular = TagFactory(name='Popular')
        tag_rare = TagFactory(name='Rare')
        
        # Popular tag on 3 locations
        for _ in range(3):
            loc = LocationFactory()
            loc.tags.add(tag_popular)
        
        # Rare tag on 1 location
        loc = LocationFactory()
        loc.tags.add(tag_rare)
        
        qs = Location.objects.all()
        tags = list(get_tags_from_queryset(qs))
        
        assert tags[0]['id'] == tag_popular.id
        assert tags[0]['location_count'] == 3
        assert tags[1]['id'] == tag_rare.id
        assert tags[1]['location_count'] == 1
    
    def test_respects_limit_parameter(self):
        """Returns only the specified number of tags."""
        for i in range(10):
            tag = TagFactory(name=f'Tag {i}')
            loc = LocationFactory()
            loc.tags.add(tag)
        
        qs = Location.objects.all()
        tags = list(get_tags_from_queryset(qs, limit=5))
        
        assert len(tags) == 5
    
    def test_respects_min_usage_parameter(self):
        """Excludes tags below minimum usage threshold."""
        tag_popular = TagFactory(name='Popular')
        tag_rare = TagFactory(name='Rare')
        
        # Popular tag on 3 locations
        for _ in range(3):
            loc = LocationFactory()
            loc.tags.add(tag_popular)
        
        # Rare tag on 1 location
        loc = LocationFactory()
        loc.tags.add(tag_rare)
        
        qs = Location.objects.all()
        tags = list(get_tags_from_queryset(qs, min_usage=2))
        
        tag_ids = [t['id'] for t in tags]
        assert tag_popular.id in tag_ids
        assert tag_rare.id not in tag_ids
    
    def test_only_includes_published_tags(self):
        """Excludes tags with status != 'p'."""
        tag_published = TagFactory(name='Published', status='p')
        tag_draft = TagFactory(name='Draft', status='c')
        
        loc1 = LocationFactory()
        loc1.tags.add(tag_published)
        
        loc2 = LocationFactory()
        loc2.tags.add(tag_draft)
        
        qs = Location.objects.all()
        tags = list(get_tags_from_queryset(qs))
        
        tag_ids = [t['id'] for t in tags]
        assert tag_published.id in tag_ids
        assert tag_draft.id not in tag_ids
    
    def test_returns_correct_fields(self):
        """Returns dict with id, slug, name, location_count."""
        tag = TagFactory(name='Test Tag', slug='test-tag')
        loc = LocationFactory()
        loc.tags.add(tag)
        
        qs = Location.objects.all()
        tags = list(get_tags_from_queryset(qs))
        
        assert len(tags) == 1
        assert tags[0]['id'] == tag.id
        assert tags[0]['slug'] == 'test-tag'
        assert tags[0]['name'] == 'Test Tag'
        assert tags[0]['location_count'] == 1


# ------------------------------------------------------------------ #
#  get_categories_from_queryset
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetCategoriesFromQueryset:
    """Test category extraction - similar to tags."""
    
    def test_returns_categories_from_queryset(self):
        """Returns categories used by locations in queryset."""
        cat1 = CategoryFactory(name='Camping')
        cat2 = CategoryFactory(name='Hotel')
        
        loc1 = LocationFactory()
        loc1.categories.add(cat1)
        
        loc2 = LocationFactory()
        loc2.categories.add(cat2)
        
        qs = Location.objects.all()
        categories = list(get_categories_from_queryset(qs))
        
        cat_ids = [c['id'] for c in categories]
        assert cat1.id in cat_ids
        assert cat2.id in cat_ids
    
    def test_orders_by_usage_count(self):
        """Most-used categories appear first."""
        cat_popular = CategoryFactory(name='Popular')
        cat_rare = CategoryFactory(name='Rare')
        
        for _ in range(5):
            loc = LocationFactory()
            loc.categories.add(cat_popular)
        
        loc = LocationFactory()
        loc.categories.add(cat_rare)
        
        qs = Location.objects.all()
        categories = list(get_categories_from_queryset(qs))
        
        assert categories[0]['id'] == cat_popular.id
        assert categories[0]['location_count'] == 5


# ------------------------------------------------------------------ #
#  get_countries_with_locations
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetCountriesWithLocations:
    
    def test_returns_countries_from_queryset(self):
        """Returns unique countries from location queryset."""
        # Create hierarchy: Netherlands > Utrecht > Amsterdam
        netherlands = RegionFactory(name='Netherlands', parent=None, level='country')
        utrecht = RegionFactory(name='Utrecht', parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')
        
        loc = LocationFactory(geo=amsterdam)
        
        qs = Location.objects.all()
        countries = list(get_countries_with_locations(qs))
        
        assert len(countries) == 1
        assert countries[0]['geo__parent__parent__name'] == 'Netherlands'
        assert countries[0]['geo__parent__parent__slug'] == netherlands.slug
    
    def test_returns_distinct_countries(self):
        """Doesn't duplicate countries with multiple locations."""
        netherlands = RegionFactory(name='Netherlands', parent=None, level='country')
        utrecht = RegionFactory(name='Utrecht', parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')
        
        LocationFactory(geo=amsterdam)
        LocationFactory(geo=amsterdam)
        
        qs = Location.objects.all()
        countries = list(get_countries_with_locations(qs))
        
        assert len(countries) == 1
    
    def test_excludes_locations_without_country(self):
        """Doesn't include locations without full region hierarchy."""
        loc = LocationFactory(geo=None)
        
        qs = Location.objects.all()
        countries = list(get_countries_with_locations(qs))
        
        assert len(countries) == 0
    
    def test_uses_all_locations_if_queryset_none(self):
        """If queryset=None, uses all locations."""
        netherlands = RegionFactory(name='Netherlands', parent=None, level='country')
        utrecht = RegionFactory(name='Utrecht', parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')
        
        LocationFactory(geo=amsterdam)
        
        countries = list(get_countries_with_locations(queryset=None))
        
        assert len(countries) == 1
        assert countries[0]['geo__parent__parent__name'] == 'Netherlands'


# ------------------------------------------------------------------ #
#  Integration test
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationQueriesIntegration:
    """Test that services work together correctly."""
    
    def test_can_get_all_filter_options_for_locations(self):
        """Verify we can get countries, categories, tags from same queryset."""
        # Setup hierarchy
        netherlands = RegionFactory(name='Netherlands', parent=None, level='country')
        utrecht = RegionFactory(name='Utrecht', parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')
        
        # Setup categories and tags
        camping = CategoryFactory(name='Camping')
        pet_friendly = TagFactory(name='Pet Friendly')
        
        # Create location with everything
        loc = LocationFactory(geo=amsterdam)
        loc.categories.add(camping)
        loc.tags.add(pet_friendly)
        
        qs = Location.objects.all()
        
        # Get all filter options
        countries = list(get_countries_with_locations(qs))
        categories = list(get_categories_from_queryset(qs))
        tags = list(get_tags_from_queryset(qs))
        
        assert len(countries) == 1
        assert len(categories) == 1
        assert len(tags) == 1
        
        assert countries[0]['geo__parent__parent__name'] == 'Netherlands'
        assert categories[0]['name'] == 'Camping'
        assert tags[0]['name'] == 'Pet Friendly'


# ------------------------------------------------------------------ #
#  get_regions_with_locations
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetRegionsWithLocations:

    def test_returns_regions_from_queryset(self):
        netherlands = RegionFactory(name='Netherlands', parent=None, level='country')
        utrecht = RegionFactory(name='Utrecht', parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')
        LocationFactory(geo=amsterdam)

        qs = Location.objects.all()
        regions = list(get_regions_with_locations(qs))

        assert len(regions) == 1
        assert regions[0]['geo__parent__name'] == 'Utrecht'
        assert regions[0]['geo__parent__slug'] == utrecht.slug

    def test_returns_distinct_regions(self):
        netherlands = RegionFactory(name='Netherlands', parent=None, level='country')
        utrecht = RegionFactory(name='Utrecht', parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')

        LocationFactory(geo=amsterdam)
        LocationFactory(geo=amsterdam)

        qs = Location.objects.all()
        regions = list(get_regions_with_locations(qs))

        assert len(regions) == 1

    def test_excludes_locations_without_region(self):
        LocationFactory(geo=None)

        qs = Location.objects.all()
        regions = list(get_regions_with_locations(qs))

        assert len(regions) == 0

    def test_uses_all_locations_if_queryset_none(self):
        netherlands = RegionFactory(name='Netherlands', parent=None, level='country')
        utrecht = RegionFactory(name='Utrecht', parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')
        LocationFactory(geo=amsterdam)

        regions = list(get_regions_with_locations(queryset=None))

        assert len(regions) == 1
        assert regions[0]['geo__parent__name'] == 'Utrecht'

    def test_ordered_alphabetically(self):
        nl = RegionFactory(parent=None, level='country')
        z_region = RegionFactory(name='Zuid-Holland', parent=nl, level='region')
        a_region = RegionFactory(name='Amsterdam', parent=nl, level='region')
        z_dept = RegionFactory(name='Z-dept', parent=z_region, level='department')
        a_dept = RegionFactory(name='A-dept', parent=a_region, level='department')

        LocationFactory(geo=z_dept)
        LocationFactory(geo=a_dept)

        qs = Location.objects.all()
        regions = list(get_regions_with_locations(qs))

        assert regions[0]['geo__parent__name'] == 'Amsterdam'
        assert regions[1]['geo__parent__name'] == 'Zuid-Holland'


# ------------------------------------------------------------------ #
#  get_departments_with_locations
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetDepartmentsWithLocations:

    def test_returns_departments_from_queryset(self):
        netherlands = RegionFactory(name='Netherlands', parent=None, level='country')
        utrecht = RegionFactory(name='Utrecht', parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')
        LocationFactory(geo=amsterdam)

        qs = Location.objects.all()
        departments = list(get_departments_with_locations(qs))

        assert len(departments) == 1
        assert departments[0]['geo__name'] == 'Amsterdam'
        assert departments[0]['geo__slug'] == amsterdam.slug

    def test_returns_distinct_departments(self):
        netherlands = RegionFactory(parent=None, level='country')
        utrecht = RegionFactory(parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')

        LocationFactory(geo=amsterdam)
        LocationFactory(geo=amsterdam)

        qs = Location.objects.all()
        departments = list(get_departments_with_locations(qs))

        assert len(departments) == 1

    def test_excludes_locations_without_geo(self):
        LocationFactory(geo=None)

        qs = Location.objects.all()
        departments = list(get_departments_with_locations(qs))

        assert len(departments) == 0

    def test_uses_all_locations_if_queryset_none(self):
        netherlands = RegionFactory(parent=None, level='country')
        utrecht = RegionFactory(parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=utrecht, level='department')
        LocationFactory(geo=amsterdam)

        departments = list(get_departments_with_locations(queryset=None))

        assert len(departments) == 1

    def test_ordered_alphabetically(self):
        nl = RegionFactory(parent=None, level='country')
        region = RegionFactory(parent=nl, level='region')
        z_dept = RegionFactory(name='Zeeland', parent=region, level='department')
        a_dept = RegionFactory(name='Arnhem', parent=region, level='department')

        LocationFactory(geo=z_dept)
        LocationFactory(geo=a_dept)

        qs = Location.objects.all()
        departments = list(get_departments_with_locations(qs))

        assert departments[0]['geo__name'] == 'Arnhem'
        assert departments[1]['geo__name'] == 'Zeeland'

# ------------------------------------------------------------------ #
#  get_sizes_for_categories
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetSizesForCategories:

  def test_returns_sizes_for_matching_categories(self):
    from locations.services.location_queries import get_sizes_for_categories
    cat = CategoryFactory()
    size = SizeFactory(status='p')
    size.categories.add(cat)
    result = list(get_sizes_for_categories([cat.pk]))
    assert size in result

  def test_excludes_non_published_sizes(self):
    from locations.services.location_queries import get_sizes_for_categories
    cat = CategoryFactory()
    size = SizeFactory(status='c')
    size.categories.add(cat)
    result = list(get_sizes_for_categories([cat.pk]))
    assert size not in result

  def test_returns_empty_for_no_matching_categories(self):
    from locations.services.location_queries import get_sizes_for_categories
    result = list(get_sizes_for_categories([9999]))
    assert result == []
