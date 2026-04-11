import pytest
from django.utils.text import slugify

from locations.models import Location
from locations.tests.factories import LocationFactory, UserFactory, RegionFactory, CategoryFactory, SizeFactory


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def location(db):
    return LocationFactory()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def activity_category(db):
    """Root 'Activity' category."""
    return CategoryFactory(name='Activity', parent=None)


@pytest.fixture
def accommodation_category(db):
    """Root 'Accommodation' category."""
    return CategoryFactory(name='Hotels', parent=None)


@pytest.fixture
def sub_activity_category(db, activity_category):
    """Child category under Activity."""
    return CategoryFactory(name='Museums', parent=activity_category)


# ------------------------------------------------------------------ #
#  Basic field & string representation
# ------------------------------------------------------------------ #

class TestLocationBasics:

    def test_str_returns_name(self, location):
        assert str(location) == location.name

    def test_name_is_required(self, db):
        """Location without a name should fail model validation."""
        from django.core.exceptions import ValidationError
        location = LocationFactory.build(name='')
        with pytest.raises(ValidationError):
            location.full_clean()

    def test_default_ordering_is_by_name(self, db):
        LocationFactory(name='Zoo')
        LocationFactory(name='Aquarium')
        LocationFactory(name='Museum')
        names = list(Location.objects.values_list('name', flat=True))
        assert names == sorted(names)


# ------------------------------------------------------------------ #
#  Slug generation
# ------------------------------------------------------------------ #

class TestLocationSlug:

    def test_slug_auto_generated_from_name(self, db):
        location = LocationFactory(name='Central Park', slug='')
        assert location.slug == slugify('Central Park')

    def test_slug_not_overwritten_if_provided(self, db):
        location = LocationFactory(name='Central Park', slug='my-custom-slug')
        assert location.slug == 'my-custom-slug'

    def test_slug_handles_accented_characters(self, db):
        location = LocationFactory(name='Café de Flore', slug='')
        assert location.slug == slugify('Café de Flore')

    def test_slug_handles_ampersand(self, db):
        location = LocationFactory(name='Fish & Chips', slug='')
        assert location.slug == slugify('Fish & Chips')

    def test_slug_is_unique(self, db):
        LocationFactory(slug='duplicate-slug')
        with pytest.raises(Exception):
            LocationFactory(slug='duplicate-slug')


# ------------------------------------------------------------------ #
#  Optional fields
# ------------------------------------------------------------------ #

class TestLocationOptionalFields:

    def test_address_is_optional(self, db):
        location = LocationFactory(address=None)
        assert location.address is None

    def test_email_is_optional(self, db):
        location = LocationFactory(email=None)
        assert location.email is None

    def test_phone_is_optional(self, db):
        location = LocationFactory(phone=None)
        assert location.phone is None

    def test_owners_name_is_optional(self, db):
        location = LocationFactory(owners_name=None)
        assert location.owners_name is None

    def test_coordinates_are_optional(self, db):
        location = LocationFactory(coord_lat=None, coord_lon=None)
        assert location.coord_lat is None
        assert location.coord_lon is None

    def test_coordinates_accept_valid_values(self, db):
        location = LocationFactory(coord_lat=52.3676, coord_lon=4.9041)
        assert location.coord_lat == pytest.approx(52.3676)
        assert location.coord_lon == pytest.approx(4.9041)


# ------------------------------------------------------------------ #
#  Type flags
# ------------------------------------------------------------------ #

class TestLocationTypes:

    def test_default_is_accommodation(self, db):
        location = LocationFactory()
        assert location.is_accommodation is True
        assert location.is_activity is False

    def test_activity_category_sets_is_activity_flag(self, db, activity_category):
        location = LocationFactory()
        location.categories.add(activity_category)
        location._update_types()
        location.save()
        location.refresh_from_db()
        assert location.is_activity is True

    def test_sub_activity_category_sets_is_activity_flag(self, db, sub_activity_category):
        location = LocationFactory()
        location.categories.add(sub_activity_category)
        location._update_types()
        location.save()
        location.refresh_from_db()
        assert location.is_activity is True

    def test_accommodation_category_sets_is_accommodation_flag(self, db, accommodation_category):
        location = LocationFactory()
        location.categories.add(accommodation_category)
        location._update_types()
        location.save()
        location.refresh_from_db()
        assert location.is_accommodation is True
        assert location.is_activity is False

    def test_both_categories_sets_both_flags(self, db, activity_category, accommodation_category):
        location = LocationFactory()
        location.categories.add(activity_category, accommodation_category)
        location._update_types()
        location.save()
        location.refresh_from_db()
        assert location.is_activity is True
        assert location.is_accommodation is True

    def test_no_categories_defaults_to_accommodation(self, db):
        location = LocationFactory()
        location._update_types()
        location.save()
        location.refresh_from_db()
        # Should remain at default since no categories
        assert location.is_accommodation is True
        assert location.is_activity is False

    def test_can_filter_by_activity(self, db, activity_category):
        activity_loc = LocationFactory()
        activity_loc.categories.add(activity_category)
        activity_loc._update_types()
        activity_loc.save()
        
        accommodation_loc = LocationFactory()
        
        activities = Location.objects.filter(is_activity=True)
        assert activity_loc in activities
        assert accommodation_loc not in activities

    def test_can_filter_by_accommodation(self, db, accommodation_category):
        accommodation_loc = LocationFactory()
        accommodation_loc.categories.add(accommodation_category)
        accommodation_loc._update_types()
        accommodation_loc.save()
        
        accommodations = Location.objects.filter(is_accommodation=True)
        assert accommodation_loc in accommodations


# ------------------------------------------------------------------ #
#  Categories M2M
# ------------------------------------------------------------------ #

class TestLocationCategories:

    def test_categories_is_optional(self, db):
        location = LocationFactory()
        assert location.categories.count() == 0

    def test_can_add_category(self, db):
        location = LocationFactory()
        category = CategoryFactory()
        location.categories.add(category)
        assert category in location.categories.all()

    def test_can_add_multiple_categories(self, db):
        location = LocationFactory()
        cat1 = CategoryFactory()
        cat2 = CategoryFactory()
        location.categories.add(cat1, cat2)
        assert location.categories.count() == 2

    def test_category_reverse_relation(self, db):
        location = LocationFactory()
        category = CategoryFactory()
        location.categories.add(category)
        assert location in category.locations.all()


# ------------------------------------------------------------------ #
#  BaseModel inheritance
# ------------------------------------------------------------------ #

class TestLocationBaseModel:

    def test_token_is_auto_generated(self, location):
        assert location.token is not None
        assert len(location.token) >= 10

    def test_token_is_unique(self, db):
        loc1 = LocationFactory()
        loc2 = LocationFactory()
        assert loc1.token != loc2.token

    def test_date_created_is_set(self, location):
        assert location.date_created is not None

    def test_date_modified_updates_on_save(self, location):
        original = location.date_modified
        location.name = 'Updated Name'
        location.save()
        location.refresh_from_db()
        assert location.date_modified > original

    def test_default_status_is_published(self, db):
        location = LocationFactory()
        assert location.status == 'p'

    def test_user_fk_is_nullable(self, db):
        location = LocationFactory(user=None)
        assert location.user is None

    def test_ajax_slug_with_slug(self, location):
        expected = f'{location.id}-{location.slug}'
        assert location.ajax_slug == expected

    def test_disallow_access_fields(self, location):
        assert 'id' in location.disallow_access_fields
        assert 'slug' in location.disallow_access_fields

    def test_get_model_fields_includes_name(self, location):
        assert 'name' in location.get_model_fields()


# ------------------------------------------------------------------ #
#  VisibilityModel inheritance
# ------------------------------------------------------------------ #

class TestLocationVisibility:

    def test_default_visibility_is_community(self):
        field = Location._meta.get_field('visibility')
        assert field.default == 'p'

    def test_visibility_choices_returns_dict(self, location):
        choices = location.get_visibility_choices()
        assert isinstance(choices, dict)
        assert 'p' in choices
        assert 'c' in choices

    def test_visibility_can_be_set_to_public(self, db):
        location = LocationFactory(visibility='p')
        assert location.visibility == 'p'

    def test_visibility_can_be_set_to_private(self, db):
        location = LocationFactory(visibility='q')
        assert location.visibility == 'q'


# ------------------------------------------------------------------ #
#  Region FK
# ------------------------------------------------------------------ #

class TestLocationRegion:

    def test_region_is_optional(self, db):
        location = LocationFactory(geo=None)
        assert location.geo is None

    def test_location_can_have_region(self, db):
        region = RegionFactory()
        location = LocationFactory(geo=region)
        assert location.geo == region

    def test_region_deleted_sets_location_region_to_null(self, db):
        region = RegionFactory()
        location = LocationFactory(geo=region)
        region.delete()
        location.refresh_from_db()
        assert location.geo is None

    def test_region_reverse_relation(self, db):
        region = RegionFactory()
        location = LocationFactory(geo=region)
        assert location in region.locations.all()

# ------------------------------------------------------------------ #
#  Service Delegation Tests
# ------------------------------------------------------------------ #

class TestLocationServiceDelegation:
    """Test that Location model correctly delegates to services."""

    def test_get_tags_from_queryset_delegates_to_service(self, db):
        """Verify Location.get_tags_from_queryset() calls the service."""
        from unittest.mock import patch
        
        qs = Location.objects.all()
        
        with patch('locations.services.location_queries.get_tags_from_queryset') as mock_service:
            mock_service.return_value = []
            
            result = Location.get_tags_from_queryset(qs, limit=10, min_usage=2)
            
            mock_service.assert_called_once_with(qs, limit=10, min_usage=2)
    
    def test_get_categories_from_queryset_delegates_to_service(self, db):
        """Verify Location.get_categories_from_queryset() calls the service."""
        from unittest.mock import patch
        
        qs = Location.objects.all()
        
        with patch('locations.services.location_queries.get_categories_from_queryset') as mock_service:
            mock_service.return_value = []
            
            result = Location.get_categories_from_queryset(qs, limit=15, min_usage=1)
            
            mock_service.assert_called_once_with(qs, limit=15, min_usage=1)
    
    def test_get_countries_with_locations_delegates_to_service(self, db):
        """Verify Location.get_countries_with_locations() calls the service."""
        from unittest.mock import patch
        
        qs = Location.objects.all()
        
        with patch('locations.services.location_queries.get_countries_with_locations') as mock_service:
            mock_service.return_value = []
            
            result = Location.get_countries_with_locations(qs)
            
            mock_service.assert_called_once_with(qs)
    
    def test_geocode_delegates_to_service(self, location):
        """Verify location.geocode() calls the service."""
        from unittest.mock import patch, Mock
        
        mock_request = Mock()
        
        with patch('locations.services.location_geocoding.geocode_location') as mock_service:
            mock_service.return_value = (52.0, 5.0)
            
            result = location.geocode(request=mock_request)
            
            mock_service.assert_called_once_with(location, request=mock_request)
    
    def test_calculate_distance_delegates_to_service(self, location):
        """Verify location.calculate_distance() calls the service."""
        from unittest.mock import patch, Mock
        
        mock_request = Mock()
        
        with patch('locations.services.location_distance.calculate_distance_to_departure_center') as mock_service:
            mock_service.return_value = 100
            
            result = location.calculate_distance_to_departure_center(request=mock_request)
            
            mock_service.assert_called_once_with(location, request=mock_request)

@pytest.mark.django_db
class TestLocationOwnedComments:

    def _setup(self, user):
        from django.contrib.contenttypes.models import ContentType
        from django.test import RequestFactory
        from locations.tests.factories import CommentFactory
        location = LocationFactory()
        ct = ContentType.objects.get_for_model(location)
        rf = RequestFactory()
        request = rf.get('/')
        request.user = user
        return location, ct, request

    def test_returns_own_comments(self):
        from django.contrib.contenttypes.models import ContentType
        from locations.tests.factories import CommentFactory
        user = UserFactory()
        location, ct, request = self._setup(user)
        comment = CommentFactory(content_type=ct, object_id=location.pk, user=user, visibility='p')
        location.request = request
        assert comment in location.owned_comments()

    def test_excludes_other_users_comments(self):
        from django.contrib.contenttypes.models import ContentType
        from locations.tests.factories import CommentFactory
        user = UserFactory()
        other = UserFactory()
        location, ct, request = self._setup(user)
        comment = CommentFactory(content_type=ct, object_id=location.pk, user=other, visibility='p')
        location.request = request
        assert comment not in location.owned_comments()

    def test_empty_without_request(self):
        from django.contrib.contenttypes.models import ContentType
        from locations.tests.factories import CommentFactory
        user = UserFactory()
        location, ct, _ = self._setup(user)
        CommentFactory(content_type=ct, object_id=location.pk, user=user, visibility='p')
        assert location.owned_comments().count() == 0


# ------------------------------------------------------------------ #
#  filtered_* fallback (no request — public-only)
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationFilteredNoRequest:

    def test_filtered_comments_public_only_without_request(self):
        from django.contrib.contenttypes.models import ContentType
        from locations.tests.factories import CommentFactory
        location = LocationFactory()
        ct = ContentType.objects.get_for_model(location)
        public = CommentFactory(content_type=ct, object_id=location.pk, visibility='p')
        community = CommentFactory(content_type=ct, object_id=location.pk, visibility='c')
        result = list(location.filtered_comments())
        assert public in result
        assert community not in result

    def test_filtered_tags_public_only_without_request(self):
        from locations.tests.factories import TagFactory
        location = LocationFactory()
        tag = TagFactory(visibility='p')
        community_tag = TagFactory(visibility='c')
        location.tags.add(tag, community_tag)
        result = list(location.filtered_tags())
        assert tag in result
        assert community_tag not in result


# ------------------------------------------------------------------ #
#  type property
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationType:

  def test_type_is_activity_when_only_activity(self, db):
    activity_root = CategoryFactory(name='Activity', parent=None)
    location = LocationFactory()
    location.categories.add(activity_root)
    location._update_types()
    assert str(location.type) == 'activity'

  def test_type_is_accommodation_when_only_accommodation(self, db):
    category = CategoryFactory(name='Hotels', parent=None)
    location = LocationFactory()
    location.categories.add(category)
    location._update_types()
    assert str(location.type) == 'accommodation'

  def test_type_is_mixed_when_both_flags_set(self, db):
    location = LocationFactory()
    location.is_accommodation = True
    location.is_activity = True
    assert str(location.type) == 'mixed'


# ------------------------------------------------------------------ #
#  favorited_by / is_visited / is_favorite
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationUserInteractions:

  def test_favorited_by_returns_users_who_favorited(self, db):
    from locations.models.Preferences import UserPreferences
    user = UserFactory()
    location = LocationFactory()
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    prefs.favorites.add(location)

    result = location.favorited_by
    assert user in result

  def test_is_visited_true_when_user_is_visitor(self, db):
    from django.test import RequestFactory
    from unittest.mock import MagicMock
    user = UserFactory()
    location = LocationFactory()
    from locations.models import Visits
    Visits.objects.create(user=user, location=location, year=2024)

    request = MagicMock()
    request.user = user
    location.request = request

    assert location.is_visited() is True

  def test_is_visited_false_when_user_not_visitor(self, db):
    from unittest.mock import MagicMock
    user = UserFactory()
    location = LocationFactory()

    request = MagicMock()
    request.user = user
    location.request = request

    assert location.is_visited() is False

  def test_is_favorite_true_when_user_favorited(self, db):
    from locations.models.Preferences import UserPreferences
    from unittest.mock import MagicMock
    user = UserFactory()
    location = LocationFactory()
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    prefs.favorites.add(location)

    request = MagicMock()
    request.user = user
    location.request = request

    assert location.is_favorite() is True

  def test_is_favorite_false_without_request(self, db):
    location = LocationFactory()
    assert location.is_favorite() is False


# ------------------------------------------------------------------ #
#  get_address_display / country / department
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationAccessHelpers:

  def test_get_address_display_formats_commas(self, db):
    location = LocationFactory(address='Rue de la Paix, Paris, France')
    assert '<br>' in location.get_address_display()

  def test_get_address_display_empty_when_no_address(self, db):
    location = LocationFactory(address=None)
    assert location.get_address_display() == ''

  def test_country_returns_none_without_geo(self, db):
    location = LocationFactory(geo=None)
    assert location.country is None

  def test_department_returns_none_without_geo(self, db):
    location = LocationFactory(geo=None)
    assert location.department is None

  def test_country_returns_top_level_region(self, db):
    country = RegionFactory(parent=None)
    region  = RegionFactory(parent=country)
    dept    = RegionFactory(parent=region)
    location = LocationFactory(geo=dept)
    assert location.country == country

  def test_department_returns_geo_directly(self, db):
    country = RegionFactory(parent=None)
    region  = RegionFactory(parent=country)
    dept    = RegionFactory(parent=region)
    location = LocationFactory(geo=dept)
    assert location.department == dept


# ------------------------------------------------------------------ #
#  Manager proxy methods
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationManagerProxies:

  def test_with_relations_returns_queryset(self, db):
    LocationFactory()
    qs = Location.objects.with_relations()
    assert qs.count() == 1

  def test_with_distances_returns_queryset(self, db):
    LocationFactory()
    qs = Location.objects.with_distances()
    assert qs.count() == 1


# ------------------------------------------------------------------ #
#  Service delegation methods (smoke tests)
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationServiceDelegation:

  def test_fetch_address_delegates_to_service(self, db):
    from unittest.mock import patch
    location = LocationFactory(address=None)
    with patch('locations.services.location_geocoding.fetch_address', return_value='Test St') as mock:
      location.fetch_address()
    mock.assert_called_once_with(location, request=None)

  def test_geocode_delegates_to_service(self, db):
    from unittest.mock import patch
    location = LocationFactory(address='Amsterdam')
    with patch('locations.services.location_geocoding.geocode_location', return_value=(52.0, 4.0)) as mock:
      result = location.geocode()
    mock.assert_called_once_with(location, request=None)
    assert result == (52.0, 4.0)

  def test_enrich_delegates_to_service(self, db):
    from unittest.mock import patch
    location = LocationFactory()
    with patch('locations.services.location_geocoding.enrich_location') as mock:
      location.enrich()
    mock.assert_called_once_with(location, request=None)

  def test_fetch_place_id_delegates_to_service(self, db):
    from unittest.mock import patch
    location = LocationFactory()
    with patch('locations.services.location_geocoding.fetch_place_id', return_value='ChIJ') as mock:
      result = location.fetch_place_id()
    mock.assert_called_once_with(location)
    assert result == 'ChIJ'

  def test_fetch_phone_delegates_to_service(self, db):
    from unittest.mock import patch
    location = LocationFactory()
    with patch('locations.services.location_geocoding.fetch_phone', return_value='+31 20 123') as mock:
      result = location.fetch_phone()
    mock.assert_called_once_with(location)
    assert result == '+31 20 123'

  def test_get_regions_with_locations_delegates_to_service(self, db):
    from unittest.mock import patch
    qs = Location.objects.all()
    with patch('locations.services.location_queries.get_regions_with_locations') as mock:
      mock.return_value = []
      Location.get_regions_with_locations(qs)
    mock.assert_called_once_with(qs)

  def test_get_departments_with_locations_delegates_to_service(self, db):
    from unittest.mock import patch
    qs = Location.objects.all()
    with patch('locations.services.location_queries.get_departments_with_locations') as mock:
      mock.return_value = []
      Location.get_departments_with_locations(qs)
    mock.assert_called_once_with(qs)


# ------------------------------------------------------------------ #
#  get_absolute_url / get_type_list_url
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationUrls:

  def test_get_absolute_url_activity(self, db):
    from locations.tests.factories import CategoryFactory
    root = CategoryFactory(name='Activity', parent=None)
    cat = CategoryFactory(parent=root)
    location = LocationFactory()
    location.categories.add(cat)
    location._update_types()
    location.save()
    assert 'activity' in str(location.get_absolute_url())

  def test_get_type_list_url_accommodation(self, db):
    location = LocationFactory(is_accommodation=True, is_activity=False)
    from django.urls import reverse
    assert str(location.get_type_list_url()) == reverse('locations:accommodations')

  def test_get_type_list_url_activity(self, db):
    from locations.tests.factories import CategoryFactory
    root = CategoryFactory(name='Activity', parent=None)
    cat = CategoryFactory(parent=root)
    location = LocationFactory()
    location.categories.add(cat)
    location._update_types()
    location.save()
    from django.urls import reverse
    assert str(location.get_type_list_url()) == reverse('locations:activities')

  def test_get_type_list_url_no_type(self, db):
    location = LocationFactory()
    # Bypass save() / _update_types() to force both flags off
    Location.objects.filter(pk=location.pk).update(is_accommodation=False, is_activity=False)
    location.refresh_from_db()
    from django.urls import reverse
    assert str(location.get_type_list_url()) == reverse('locations:all')


# ------------------------------------------------------------------ #
#  _update_types edge cases
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationUpdateTypesEdgeCases:

  def test_no_categories_preserves_existing_accommodation_flag(self, db):
    """When no categories exist and is_accommodation is already True, keep it."""
    location = LocationFactory()
    location.categories.clear()
    location.is_accommodation = True
    location.is_activity = False
    location._update_types()
    assert location.is_accommodation is True

  def test_no_categories_preserves_existing_activity_flag(self, db):
    """When no categories exist and is_activity is already True, keep it."""
    location = LocationFactory()
    location.categories.clear()
    location.is_accommodation = False
    location.is_activity = True
    location._update_types()
    assert location.is_activity is True

  def test_no_categories_both_flags_false_defaults_to_accommodation(self, db):
    """When no categories and both flags are False, default to is_accommodation=True."""
    location = LocationFactory()
    location.categories.clear()
    location.is_accommodation = False
    location.is_activity = False
    location._update_types()
    assert location.is_accommodation is True
    assert location.is_activity is False


# ------------------------------------------------------------------ #
#  is_visited / is_favorite — no request
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationSearchableFunctionsNoRequest:

  def test_is_visited_false_without_request(self, db):
    location = LocationFactory()
    assert location.is_visited() is False

  def test_is_favorite_false_without_request(self, db):
    location = LocationFactory()
    assert location.is_favorite() is False


# ------------------------------------------------------------------ #
#  available_sizes
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationAvailableSizes:

  def test_available_sizes_empty_when_no_size_for_category(self, db):
    location = LocationFactory()
    sizes = location.available_sizes()
    assert sizes.count() == 0


# ------------------------------------------------------------------ #
#  completeness — size bonus
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationCompletenessSize:

  def _location_with_size(self):
    """Return a location with a Size linked to its category and set on the location."""
    category = CategoryFactory()
    size = SizeFactory()
    size.categories.add(category)
    location = LocationFactory()
    location.categories.add(category)
    location.size = size
    location.save()
    return location

  def test_size_bonus_included_in_completeness_when_size_set(self, db):
    location = self._location_with_size()
    location.size = None
    location.save()
    location.calculate_completeness()
    score_without_size = location.completeness

    location2 = self._location_with_size()
    location2.calculate_completeness()
    score_with_size = location2.completeness

    assert score_with_size > score_without_size

  def test_completeness_hints_includes_size_hint_when_applicable(self, db):
    location = self._location_with_size()
    labels = [label for label, _ in location.completeness_hints()]
    from django.utils.translation import gettext as _
    assert any('size' in str(label).lower() for label in labels)

  def test_completeness_hints_size_bonus_when_size_set(self, db):
    location = self._location_with_size()
    hints = dict(location.completeness_hints())
    from django.utils.translation import gettext as _
    size_hint = next((v for k, v in hints.items() if 'size' in str(k).lower()), None)
    assert size_hint == 'bonus'

  def test_completeness_hints_size_missing_when_size_not_set(self, db):
    category = CategoryFactory()
    size = SizeFactory()
    size.categories.add(category)
    location = LocationFactory()
    location.categories.add(category)
    # size applicable but not set
    hints = dict(location.completeness_hints())
    size_hint = next((v for k, v in hints.items() if 'size' in str(k).lower()), None)
    assert size_hint == 'missing'


# ------------------------------------------------------------------ #
#  nearby
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationNearby:

  def test_nearby_no_request_uses_nearby_range(self, db):
    from unittest.mock import patch, MagicMock
    location = LocationFactory()
    with patch('locations.services.location_nearby.get_nearby_locations', return_value=[]) as mock:
      location.nearby()
    mock.assert_called_once()
    _, kwargs = mock.call_args
    assert kwargs.get('radius_km') is not None or mock.call_args[0]

  def test_nearby_with_guest_uses_guest_range(self, db):
    from unittest.mock import patch, MagicMock
    from django.conf import settings
    location = LocationFactory()
    request = MagicMock()
    request.user.is_authenticated = False
    location.request = request
    expected = getattr(settings, 'GUEST_NEARBY_RANGE', 35)
    with patch('locations.services.location_nearby.get_nearby_locations', return_value=[]) as mock:
      location.nearby()
    _, kwargs = mock.call_args
    assert kwargs.get('radius_km') == expected

  def test_nearby_with_auth_user_uses_nearby_range_by_default(self, db):
    from unittest.mock import patch, MagicMock
    from django.conf import settings
    location = LocationFactory()
    request = MagicMock()
    request.user.is_authenticated = True
    request.GET.get = MagicMock(return_value=0)
    location.request = request
    expected = getattr(settings, 'NEARBY_RANGE', 75)
    with patch('locations.services.location_nearby.get_nearby_locations', return_value=[]) as mock:
      location.nearby()
    _, kwargs = mock.call_args
    assert kwargs.get('radius_km') == expected

  def test_nearby_with_auth_user_respects_radius_param(self, db):
    from unittest.mock import patch, MagicMock
    location = LocationFactory()
    request = MagicMock()
    request.user.is_authenticated = True
    request.GET.get = MagicMock(return_value='50')
    location.request = request
    with patch('locations.services.location_nearby.get_nearby_locations', return_value=[]) as mock:
      location.nearby()
    _, kwargs = mock.call_args
    assert kwargs.get('radius_km') == 50.0


# ------------------------------------------------------------------ #
#  ajax_function delegates (topactions, contact_details)
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationAjaxFunctions:

  def test_topactions_returns_empty_string(self, db):
    location = LocationFactory()
    assert location.topactions() == ''

  def test_contact_details_returns_empty_string(self, db):
    location = LocationFactory()
    assert location.contact_details() == ''
