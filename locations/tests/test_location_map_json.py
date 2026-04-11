"""Tests for the /json/locations/ endpoint used by map viewport loading.

Covers:
- Response structure and required map fields in model/location.json
- Bbox filtering via coord_lat__gte/lte, coord_lon__gte/lte
- Only published/visible locations are returned
"""
import json
import pytest
from django.urls import reverse

from locations.tests.factories import LocationFactory, UserFactory


def _json_locations(client, **params):
  """GET /json/locations/?format=json with optional query params."""
  url = reverse('cmnsd:dispatch', kwargs={'model': 'locations'})
  response = client.get(url, {'format': 'json', **params})
  assert response.status_code == 200
  data = json.loads(response.content)
  return data['payload']['location']


# ------------------------------------------------------------------ #
#  Response structure — map fields
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationMapJsonFields:

  def test_response_contains_location_key(self, client):
    LocationFactory(coord_lat=51.0, coord_lon=5.0)
    url = reverse('cmnsd:dispatch', kwargs={'model': 'locations'})
    response = client.get(url, {'format': 'json'})
    data = json.loads(response.content)
    assert 'location' in data['payload']

  def test_each_entry_has_coord_lat(self, client):
    loc = LocationFactory(coord_lat=51.5, coord_lon=5.1)
    entries = _json_locations(client)
    assert 'coord_lat' in entries[loc.slug]

  def test_each_entry_has_coord_lon(self, client):
    loc = LocationFactory(coord_lat=51.5, coord_lon=5.1)
    entries = _json_locations(client)
    assert 'coord_lon' in entries[loc.slug]

  def test_each_entry_has_is_accommodation(self, client):
    loc = LocationFactory()
    entries = _json_locations(client)
    assert 'is_accommodation' in entries[loc.slug]

  def test_each_entry_has_is_activity(self, client):
    loc = LocationFactory()
    entries = _json_locations(client)
    assert 'is_activity' in entries[loc.slug]

  def test_each_entry_has_url(self, client):
    loc = LocationFactory()
    entries = _json_locations(client)
    assert 'url' in entries[loc.slug]

  def test_each_entry_has_summary(self, client):
    loc = LocationFactory(summary='Nice place')
    entries = _json_locations(client)
    assert 'summary' in entries[loc.slug]

  def test_coord_values_are_numeric(self, client):
    loc = LocationFactory(coord_lat=51.5, coord_lon=5.1)
    entries = _json_locations(client)
    assert entries[loc.slug]['coord_lat'] == 51.5
    assert entries[loc.slug]['coord_lon'] == 5.1

  def test_coord_null_when_not_geocoded(self, client):
    loc = LocationFactory(coord_lat=None, coord_lon=None)
    entries = _json_locations(client)
    assert entries[loc.slug]['coord_lat'] is None
    assert entries[loc.slug]['coord_lon'] is None


# ------------------------------------------------------------------ #
#  Bbox filtering
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationMapBboxFilter:

  def test_location_inside_bbox_is_returned(self, client):
    loc = LocationFactory(coord_lat=51.5, coord_lon=5.0)
    entries = _json_locations(
      client,
      coord_lat__gte=51.0, coord_lat__lte=52.0,
      coord_lon__gte=4.5, coord_lon__lte=5.5,
    )
    assert loc.slug in entries

  def test_location_outside_bbox_is_excluded(self, client):
    loc = LocationFactory(coord_lat=48.0, coord_lon=2.0)
    entries = _json_locations(
      client,
      coord_lat__gte=51.0, coord_lat__lte=52.0,
      coord_lon__gte=4.5, coord_lon__lte=5.5,
    )
    assert loc.slug not in entries

  def test_location_on_bbox_boundary_is_returned(self, client):
    loc = LocationFactory(coord_lat=51.0, coord_lon=4.5)
    entries = _json_locations(
      client,
      coord_lat__gte=51.0, coord_lat__lte=52.0,
      coord_lon__gte=4.5, coord_lon__lte=5.5,
    )
    assert loc.slug in entries

  def test_bbox_filters_correctly_with_multiple_locations(self, client):
    inside = LocationFactory(coord_lat=51.5, coord_lon=5.0)
    outside = LocationFactory(coord_lat=43.0, coord_lon=1.0)
    entries = _json_locations(
      client,
      coord_lat__gte=51.0, coord_lat__lte=52.0,
      coord_lon__gte=4.5, coord_lon__lte=5.5,
    )
    assert inside.slug in entries
    assert outside.slug not in entries

  def test_empty_bbox_returns_no_locations(self, client):
    LocationFactory(coord_lat=51.5, coord_lon=5.0)
    # Bbox in the middle of the ocean
    entries = _json_locations(
      client,
      coord_lat__gte=0.0, coord_lat__lte=1.0,
      coord_lon__gte=0.0, coord_lon__lte=1.0,
    )
    assert len(entries) == 0

  def test_location_without_coords_excluded_from_bbox_query(self, client):
    loc = LocationFactory(coord_lat=None, coord_lon=None)
    entries = _json_locations(
      client,
      coord_lat__gte=51.0, coord_lat__lte=52.0,
      coord_lon__gte=4.5, coord_lon__lte=5.5,
    )
    assert loc.slug not in entries
