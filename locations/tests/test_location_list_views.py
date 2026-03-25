import pytest
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

from locations.models.Location import Location
from locations.tests.factories import LocationFactory, RegionFactory, UserFactory
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
#  get_region_filter_options
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestRegionFilterOptions:

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

    result = self._view(_get()).get_region_filter_options(qs)

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

    result = self._view(_get()).get_region_filter_options(qs)

    assert result['key'] == 'geo__parent__slug'
    assert len(result['options']) == 2

  def test_returns_department_key_when_single_region_multiple_departments(self, db):
    country = RegionFactory(parent=None)
    region  = RegionFactory(parent=country)
    dept_a  = RegionFactory(parent=region)
    dept_b  = RegionFactory(parent=region)
    LocationFactory(geo=dept_a)
    LocationFactory(geo=dept_b)
    qs = Location.objects.all()

    result = self._view(_get()).get_region_filter_options(qs)

    assert result['key'] == 'geo__slug'
    assert len(result['options']) == 2

  def test_returns_empty_dict_when_single_department(self, db):
    dept = _make_geo_hierarchy('nl', 'nh', 'amsterdam')
    LocationFactory(geo=dept)
    qs = Location.objects.all()

    result = self._view(_get()).get_region_filter_options(qs)

    assert result == {}

  def test_options_are_sorted_by_name(self, db):
    dept_nl = _make_geo_hierarchy('nl', 'nh', 'amsterdam')
    dept_fr = _make_geo_hierarchy('fr', 'idf', 'paris')
    # Ensure France sorts before Netherlands alphabetically
    dept_nl.parent.parent.name = 'Netherlands'
    dept_nl.parent.parent.save()
    dept_fr.parent.parent.name = 'France'
    dept_fr.parent.parent.save()
    LocationFactory(geo=dept_nl)
    LocationFactory(geo=dept_fr)
    qs = Location.objects.all()

    result = self._view(_get()).get_region_filter_options(qs)

    names = [o['name'] for o in result['options']]
    assert names == sorted(names)
