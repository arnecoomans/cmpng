import pytest
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

from locations.models.Location import Location
from locations.tests.factories import (
  LocationFactory,
  RegionFactory,
  CategoryFactory,
  TagFactory,
  UserFactory,
)
from locations.views.locations.locations_list import (
  AllLocationListView,
  AccommodationListView,
  ActivityListView,
)


def _get(user=None):
  from django.contrib.auth.models import AnonymousUser
  request = RequestFactory().get('/')
  request.user = user or AnonymousUser()
  request.session = {}
  request._messages = FallbackStorage(request)
  return request


def _make_geo_hierarchy(country_slug, region_slug, dept_slug):
  country = RegionFactory(slug=country_slug, parent=None)
  region  = RegionFactory(slug=region_slug,  parent=country)
  dept    = RegionFactory(slug=dept_slug,     parent=region)
  return dept


# ------------------------------------------------------------------ #
#  AllLocationListView
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestAllLocationListView:

  def test_returns_200(self, db):
    request = _get()
    response = AllLocationListView.as_view()(request)
    assert response.status_code == 200

  def test_scope_is_all(self, db):
    request = _get()
    response = AllLocationListView.as_view()(request)
    assert response.context_data['scope'] == 'all'

  def test_includes_all_locations(self, db):
    LocationFactory(is_accommodation=True)
    LocationFactory(is_activity=True)
    request = _get()
    response = AllLocationListView.as_view()(request)
    assert response.context_data['locations'].count() == 2


# ------------------------------------------------------------------ #
#  AccommodationListView
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestAccommodationListView:

  def test_returns_200(self, db):
    request = _get()
    response = AccommodationListView.as_view()(request)
    assert response.status_code == 200

  def test_scope_is_accommodations(self, db):
    request = _get()
    response = AccommodationListView.as_view()(request)
    assert response.context_data['scope'] == 'accommodations'

  def test_filters_to_accommodations_only(self, db):
    LocationFactory(is_accommodation=True,  is_activity=False)
    LocationFactory(is_accommodation=False, is_activity=True)
    request = _get()
    response = AccommodationListView.as_view()(request)
    qs = response.context_data['locations']
    assert all(loc.is_accommodation for loc in qs)

  def test_excludes_activity_only_locations(self, db):
    LocationFactory(is_accommodation=False, is_activity=True)
    request = _get()
    response = AccommodationListView.as_view()(request)
    assert response.context_data['locations'].count() == 0


# ------------------------------------------------------------------ #
#  ActivityListView
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestActivityListView:

  def test_returns_200(self, db):
    request = _get()
    response = ActivityListView.as_view()(request)
    assert response.status_code == 200

  def test_scope_is_activities(self, db):
    request = _get()
    response = ActivityListView.as_view()(request)
    assert response.context_data['scope'] == 'activities'

  def test_filters_to_activities_only(self, db):
    LocationFactory(is_accommodation=False, is_activity=True)
    LocationFactory(is_accommodation=True,  is_activity=False)
    request = _get()
    response = ActivityListView.as_view()(request)
    qs = response.context_data['locations']
    assert all(loc.is_activity for loc in qs)

  def test_excludes_accommodation_only_locations(self, db):
    LocationFactory(is_accommodation=True, is_activity=False)
    request = _get()
    response = ActivityListView.as_view()(request)
    assert response.context_data['locations'].count() == 0


# ------------------------------------------------------------------ #
#  get_geo_filter_options
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGeoFilterOptions:

  def _view(self, request):
    view = AllLocationListView()
    view.request = request
    view.args = []
    view.kwargs = {}
    view.object_list = Location.objects.none()
    return view

  def test_returns_country_key_when_multiple_countries(self, db):
    dept_nl = _make_geo_hierarchy('nl', 'nh', 'amsterdam')
    dept_fr = _make_geo_hierarchy('fr', 'idf', 'paris')
    LocationFactory(geo=dept_nl)
    LocationFactory(geo=dept_fr)
    qs = Location.objects.all()

    result = self._view(_get()).get_geo_filter_options(qs)

    assert result['key'] == 'country'
    assert len(result['options']) == 2

  def test_returns_region_key_when_single_country_multiple_regions(self, db):
    country = RegionFactory(parent=None)
    region_a = RegionFactory(parent=country)
    region_b = RegionFactory(parent=country)
    dept_a = RegionFactory(parent=region_a)
    dept_b = RegionFactory(parent=region_b)
    LocationFactory(geo=dept_a)
    LocationFactory(geo=dept_b)
    qs = Location.objects.all()

    result = self._view(_get()).get_geo_filter_options(qs)

    assert result['key'] == 'region'
    assert len(result['options']) == 2

  def test_returns_department_key_when_single_region_multiple_departments(self, db):
    country = RegionFactory(parent=None)
    region  = RegionFactory(parent=country)
    dept_a  = RegionFactory(parent=region)
    dept_b  = RegionFactory(parent=region)
    LocationFactory(geo=dept_a)
    LocationFactory(geo=dept_b)
    qs = Location.objects.all()

    result = self._view(_get()).get_geo_filter_options(qs)

    assert result['key'] == 'department'
    assert len(result['options']) == 2

  def test_returns_empty_dict_when_single_department(self, db):
    dept = _make_geo_hierarchy('nl', 'nh', 'amsterdam')
    LocationFactory(geo=dept)
    qs = Location.objects.all()

    result = self._view(_get()).get_geo_filter_options(qs)

    assert result == {}

  def test_options_are_sorted_by_name(self, db):
    dept_nl = _make_geo_hierarchy('nl', 'nh', 'amsterdam')
    dept_fr = _make_geo_hierarchy('fr', 'idf', 'paris')
    dept_nl.parent.parent.name = 'Netherlands'
    dept_nl.parent.parent.save()
    dept_fr.parent.parent.name = 'France'
    dept_fr.parent.parent.save()
    LocationFactory(geo=dept_nl)
    LocationFactory(geo=dept_fr)
    qs = Location.objects.all()

    result = self._view(_get()).get_geo_filter_options(qs)

    names = [o['name'] for o in result['options']]
    assert names == sorted(names)


# ------------------------------------------------------------------ #
#  get_visibility_filter_options
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestVisibilityFilterOptions:

  def _view(self, request):
    view = AllLocationListView()
    view.request = request
    view.args = []
    view.kwargs = {}
    view.object_list = Location.objects.none()
    return view

  def test_sole_visibility_returns_sole_name(self, db):
    LocationFactory(visibility='p')
    LocationFactory(visibility='p')
    qs = Location.objects.filter(status='p')

    result = self._view(_get()).get_visibility_filter_options(qs)

    assert result['sole_name'] is not None
    assert result['options'] == []

  def test_multiple_visibilities_returns_options(self, db):
    LocationFactory(visibility='p')
    LocationFactory(visibility='c')
    qs = Location.objects.filter(status='p')

    result = self._view(_get()).get_visibility_filter_options(qs)

    assert 'sole_name' not in result
    assert len(result['options']) == 2

  def test_active_visibility_excluded_from_options(self, db):
    LocationFactory(visibility='p')
    LocationFactory(visibility='c')
    qs = Location.objects.filter(status='p')
    request = RequestFactory().get('/', {'visibility': 'p'})
    from django.contrib.auth.models import AnonymousUser
    from django.contrib.messages.storage.fallback import FallbackStorage
    request.user = AnonymousUser()
    request.session = {}
    request._messages = FallbackStorage(request)

    result = self._view(request).get_visibility_filter_options(qs)

    keys = [o['key'] for o in result['options']]
    assert 'p' not in keys
    assert 'c' in keys

  def test_active_name_set_when_visibility_filtered(self, db):
    LocationFactory(visibility='p')
    LocationFactory(visibility='c')
    qs = Location.objects.filter(status='p')
    request = RequestFactory().get('/', {'visibility': 'p'})
    from django.contrib.auth.models import AnonymousUser
    request.user = AnonymousUser()
    request.session = {}
    request._messages = FallbackStorage(request)

    result = self._view(request).get_visibility_filter_options(qs)

    assert 'active_name' in result

  def test_empty_queryset_returns_empty_dict(self, db):
    qs = Location.objects.none()

    result = self._view(_get()).get_visibility_filter_options(qs)

    assert result == {}


# ------------------------------------------------------------------ #
#  get_status_filter_options / _check_extra_statuses
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStatusFilterOptions:

  def _view(self, request):
    view = AllLocationListView()
    view.request = request
    view.args = []
    view.kwargs = {}
    view.object_list = Location.objects.none()
    return view

  def test_no_extra_statuses_returns_empty_list(self, db):
    LocationFactory(status='p')
    qs = Location.objects.all()

    view = self._view(_get())
    view._check_extra_statuses(qs)

    assert view.get_status_filter_options() == []

  def test_owner_with_concept_gets_draft_option(self, db):
    user = UserFactory()
    user.save()
    LocationFactory(status='c', user=user)
    qs = Location.objects.all()
    request = _get(user)

    view = self._view(request)
    view._check_extra_statuses(qs)
    options = view.get_status_filter_options()

    keys = [o['key'] for o in options]
    assert 'p' in keys
    assert 'c' in keys
    assert 'r' not in keys

  def test_staff_with_revoked_gets_revoked_option(self, db):
    staff = UserFactory()
    staff.is_staff = True
    staff.save()
    LocationFactory(status='r')
    qs = Location.objects.all()
    request = _get(staff)

    view = self._view(request)
    view._check_extra_statuses(qs)
    options = view.get_status_filter_options()

    keys = [o['key'] for o in options]
    assert 'p' in keys
    assert 'r' in keys

  def test_anon_never_gets_extra_statuses(self, db):
    LocationFactory(status='c')
    LocationFactory(status='r')
    qs = Location.objects.all()

    view = self._view(_get())
    view._check_extra_statuses(qs)

    assert view.get_status_filter_options() == []


# ------------------------------------------------------------------ #
#  get_category_filter_options / get_tag_filter_options
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCategoryTagFilterOptions:

  def _view(self, request):
    view = AllLocationListView()
    view.request = request
    view.args = []
    view.kwargs = {}
    view.object_list = Location.objects.none()
    return view

  def test_category_options_exclude_active(self, db):
    camping = CategoryFactory(name='Camping')
    hotel = CategoryFactory(name='Hotel')
    loc = LocationFactory()
    loc.categories.add(camping)
    loc.categories.add(hotel)
    qs = Location.objects.filter(status='p')
    request = RequestFactory().get('/', {'category': camping.slug})
    from django.contrib.auth.models import AnonymousUser
    request.user = AnonymousUser()
    request.session = {}
    request._messages = FallbackStorage(request)

    result = self._view(request).get_category_filter_options(qs)

    slugs = [o['slug'] for o in result['options']]
    assert camping.slug not in slugs
    assert hotel.slug in slugs

  def test_category_options_include_precomputed_url(self, db):
    cat = CategoryFactory(name='Camping')
    loc = LocationFactory()
    loc.categories.add(cat)
    qs = Location.objects.filter(status='p')

    result = self._view(_get()).get_category_filter_options(qs)

    assert 'url' in result['options'][0]
    assert cat.slug in result['options'][0]['url']

  def test_tag_options_exclude_active(self, db):
    pet = TagFactory(name='Pet Friendly')
    pool = TagFactory(name='Pool')
    loc = LocationFactory()
    loc.tags.add(pet)
    loc.tags.add(pool)
    qs = Location.objects.filter(status='p')
    request = RequestFactory().get('/', {'tag': pet.slug})
    from django.contrib.auth.models import AnonymousUser
    request.user = AnonymousUser()
    request.session = {}
    request._messages = FallbackStorage(request)

    result = self._view(request).get_tag_filter_options(qs)

    slugs = [o['slug'] for o in result['options']]
    assert pet.slug not in slugs
    assert pool.slug in slugs

  def test_second_category_appended_with_and_separator(self, db):
    camping = CategoryFactory(name='Camping')
    hotel = CategoryFactory(name='Hotel')
    loc = LocationFactory()
    loc.categories.add(camping)
    loc.categories.add(hotel)
    qs = Location.objects.filter(status='p')
    request = RequestFactory().get('/', {'category': camping.slug})
    from django.contrib.auth.models import AnonymousUser
    request.user = AnonymousUser()
    request.session = {}
    request._messages = FallbackStorage(request)

    result = self._view(request).get_category_filter_options(qs)

    hotel_option = next(o for o in result['options'] if o['slug'] == hotel.slug)
    assert '__and__' in hotel_option['url']
