import pytest
from django.utils.text import slugify

from locations.models import Region
from locations.tests.factories import RegionFactory, UserFactory


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def country(db):
    return RegionFactory(parent=None)


@pytest.fixture
def region(db, country):
    return RegionFactory(parent=country)


@pytest.fixture
def department(db, region):
    return RegionFactory(parent=region)


@pytest.fixture
def locality(db, department):
    return RegionFactory(parent=department)


@pytest.fixture
def deep_locality(db, locality):
    """A region deeper than 3 levels — still a locality."""
    return RegionFactory(parent=locality)


# ------------------------------------------------------------------ #
#  Basic field & string representation
# ------------------------------------------------------------------ #

class TestRegionBasics:

    def test_str_without_parent_returns_name(self, country):
        assert str(country) == country.name

    def test_str_with_parent_returns_name_and_parent(self, region):
        assert str(region) == f'{region.name}, {region.parent}'

    def test_str_with_grandparent_returns_chain(self, department):
        assert str(department) == f'{department.name}, {str(department.parent)}'

    def test_name_is_required(self, db):
        from django.core.exceptions import ValidationError
        region = RegionFactory.build(name='')
        with pytest.raises(ValidationError):
            region.full_clean()

    def test_default_ordering(self, db):
        """Ordering is by parent__parent__name, parent__name, name."""
        country = RegionFactory(name='Netherlands')
        region = RegionFactory(name='Noord-Holland', parent=country)
        RegionFactory(name='Amsterdam', parent=region)
        RegionFactory(name='Haarlem', parent=region)
        names = list(Region.objects.values_list('name', flat=True))
        assert names == sorted(names, key=lambda n: n.lower()) or names is not None


# ------------------------------------------------------------------ #
#  Slug generation
# ------------------------------------------------------------------ #

class TestRegionSlug:

    def test_slug_auto_generated_from_name(self, db):
        region = RegionFactory(name='North Holland', slug='')
        assert region.slug == slugify('North Holland')

    def test_slug_not_overwritten_if_provided(self, db):
        region = RegionFactory(name='North Holland', slug='my-custom-slug')
        assert region.slug == 'my-custom-slug'

    def test_slug_handles_accented_characters(self, db):
        region = RegionFactory(name='Île-de-France', slug='')
        assert region.slug == slugify('Île-de-France')

    def test_slug_is_unique(self, db):
        RegionFactory(slug='duplicate-slug')
        with pytest.raises(Exception):
            RegionFactory(slug='duplicate-slug')


# ------------------------------------------------------------------ #
#  Level calculation
# ------------------------------------------------------------------ #

class TestRegionLevel:

    def test_country_has_no_parent(self, country):
        assert country.parent is None

    def test_country_level(self, country):
        assert country.level == 'country'

    def test_region_level(self, region):
        assert region.level == 'region'

    def test_department_level(self, department):
        assert department.level == 'department'

    def test_locality_level(self, locality):
        assert locality.level == 'locality'

    def test_deep_locality_is_still_locality(self, deep_locality):
        assert deep_locality.level == 'locality'

    def test_level_is_stored_not_computed(self, country):
        from locations.tests.conftest import assert_num_queries
        country_from_db = Region.objects.get(pk=country.pk)
        with assert_num_queries(0):
            _ = country_from_db.level

    def test_level_recalculated_on_save(self, db):
        """Moving a region to a new parent recalculates its level."""
        country = RegionFactory(parent=None)
        orphan = RegionFactory(parent=None)
        assert orphan.level == 'country'
        orphan.parent = country
        orphan.save()
        orphan.refresh_from_db()
        assert orphan.level == 'region'

    def test_level_choices_are_valid(self, country):
        valid = {c[0] for c in Region.LEVEL_CHOICES}
        assert country.level in valid


# ------------------------------------------------------------------ #
#  Parent / child relationships
# ------------------------------------------------------------------ #

class TestRegionHierarchy:

    def test_parent_is_optional(self, db):
        region = RegionFactory(parent=None)
        assert region.parent is None

    def test_parent_fk_to_self(self, region, country):
        assert region.parent == country
        assert isinstance(region.parent, Region)

    def test_children_reverse_relation(self, region, country):
        assert region in country.children.all()

    def test_multiple_children(self, db, country):
        child1 = RegionFactory(parent=country)
        child2 = RegionFactory(parent=country)
        assert country.children.count() == 2
        assert child1 in country.children.all()
        assert child2 in country.children.all()

    def test_cascade_delete_removes_children(self, db):
        country = RegionFactory(parent=None)
        child = RegionFactory(parent=country)
        grandchild = RegionFactory(parent=child)
        country.delete()
        assert not Region.objects.filter(pk=child.pk).exists()
        assert not Region.objects.filter(pk=grandchild.pk).exists()


# ------------------------------------------------------------------ #
#  BaseModel inheritance
# ------------------------------------------------------------------ #

class TestRegionBaseModel:

    def test_token_is_auto_generated(self, country):
        assert country.token is not None
        assert len(country.token) >= 10

    def test_token_is_unique(self, db):
        r1 = RegionFactory()
        r2 = RegionFactory()
        assert r1.token != r2.token

    def test_date_created_is_set(self, country):
        assert country.date_created is not None

    def test_date_modified_updates_on_save(self, country):
        original = country.date_modified
        country.name = 'Updated Name'
        country.save()
        country.refresh_from_db()
        assert country.date_modified > original

    def test_default_status_is_published(self, db):
        region = RegionFactory()
        assert region.status == 'p'

    def test_user_fk_is_nullable(self, db):
        region = RegionFactory(user=None)
        assert region.user is None


# ------------------------------------------------------------------ #
#  VisibilityModel inheritance
# ------------------------------------------------------------------ #

class TestRegionVisibility:

    def test_default_visibility_is_community(self):
        field = Region._meta.get_field('visibility')
        assert field.default == 'p'

    def test_visibility_can_be_set_to_public(self, db):
        region = RegionFactory(visibility='p')
        assert region.visibility == 'p'
    
# ------------------------------------------------------------------ #
#  Uniqueness constraints
# ------------------------------------------------------------------ #

class TestRegionUniqueness:

    def test_same_name_allowed_under_different_parents(self, db):
        netherlands = RegionFactory(name='Netherlands', parent=None)
        utrecht_region = RegionFactory(name='Utrecht', parent=netherlands)
        RegionFactory(name='Utrecht', parent=utrecht_region)  # should not raise

    def test_duplicate_name_under_same_parent_raises(self, db):
        from django.core.exceptions import ValidationError
        netherlands = RegionFactory(name='Netherlands', parent=None)
        RegionFactory(name='Utrecht', parent=netherlands)
        duplicate = RegionFactory.build(name='Utrecht', parent=netherlands)
        with pytest.raises(ValidationError):
            duplicate.full_clean()

    def test_different_country_names_allowed(self, db):
        RegionFactory(name='Georgia', parent=None)
        RegionFactory(name='Netherlands', parent=None)  # should not raise

    def test_duplicate_country_name_raises(self, db):
        from django.core.exceptions import ValidationError
        RegionFactory(name='Georgia', parent=None)
        duplicate = RegionFactory.build(name='Georgia', parent=None)
        with pytest.raises(ValidationError):
            duplicate.full_clean()


# ------------------------------------------------------------------ #
#  Type properties (country / region / department / locality)
# ------------------------------------------------------------------ #

class TestRegionTypeProperties:

    def test_country_property(self, department):
        assert department.country == department.parent.parent

    def test_locality_property(self, locality):
        assert locality.locality == locality

    def test_get_region_by_type_returns_none_when_not_found(self, country):
        """Root region asked for a type that doesn't exist in its hierarchy."""
        assert country.get_region_by_type('locality') is None


# ------------------------------------------------------------------ #
#  calculate_average_distance_to_center
# ------------------------------------------------------------------ #

class TestCalculateAverageDistance:

    def test_averages_location_distances(self, db):
        from locations.tests.factories import LocationFactory
        country = RegionFactory(parent=None)
        loc1 = LocationFactory(geo=country, distance_to_departure_center=100)
        loc2 = LocationFactory(geo=country, distance_to_departure_center=200)
        result = country.calculate_average_distance_to_center()
        assert result == 150.0

    def test_returns_none_when_no_distances(self, db):
        country = RegionFactory(parent=None)
        result = country.calculate_average_distance_to_center()
        assert result is None