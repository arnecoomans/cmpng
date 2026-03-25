import pytest
from unittest.mock import patch

from locations.services.location_nearby import haversine_km, get_nearby_locations
from locations.tests.factories import LocationFactory


# ------------------------------------------------------------------ #
#  haversine_km — pure maths, no DB needed
# ------------------------------------------------------------------ #

class TestHaversineKm:

  def test_same_point_is_zero(self):
    assert haversine_km(52.0, 5.0, 52.0, 5.0) == 0.0

  def test_known_distance_amsterdam_utrecht(self):
    # Amsterdam ≈ (52.3676, 4.9041), Utrecht ≈ (52.0907, 5.1214) — ~34 km
    dist = haversine_km(52.3676, 4.9041, 52.0907, 5.1214)
    assert 30 < dist < 40

  def test_symmetry(self):
    a_to_b = haversine_km(52.0, 4.0, 51.0, 5.0)
    b_to_a = haversine_km(51.0, 5.0, 52.0, 4.0)
    assert abs(a_to_b - b_to_a) < 0.001

  def test_returns_float(self):
    result = haversine_km(52.0, 5.0, 53.0, 6.0)
    assert isinstance(result, float)

  def test_north_south_distance(self):
    # 1 degree latitude ≈ 111 km
    dist = haversine_km(52.0, 5.0, 53.0, 5.0)
    assert 109 < dist < 113

  def test_larger_distance(self):
    # Amsterdam to Rome ≈ 1296 km
    dist = haversine_km(52.3676, 4.9041, 41.9028, 12.4964)
    assert 1200 < dist < 1400


# ------------------------------------------------------------------ #
#  get_nearby_locations
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetNearbyLocations:

  def test_returns_empty_if_location_has_no_coordinates(self, db):
    location = LocationFactory(coord_lat=None, coord_lon=None)
    result = get_nearby_locations(location)
    assert result == []

  def test_returns_empty_if_no_nearby_locations(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    # Another location far away (Paris)
    LocationFactory(coord_lat=48.8566, coord_lon=2.3522)
    result = get_nearby_locations(home, radius_km=50)
    assert result == []

  def test_returns_nearby_location_within_radius(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    # 10 km away
    nearby = LocationFactory(coord_lat=52.09, coord_lon=5.0)
    result = get_nearby_locations(home, radius_km=50)
    assert nearby in result

  def test_excludes_self(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    result = get_nearby_locations(home, radius_km=200)
    assert home not in result

  def test_excludes_locations_outside_radius(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    far = LocationFactory(coord_lat=48.8566, coord_lon=2.3522)  # Paris, ~500 km
    result = get_nearby_locations(home, radius_km=50)
    assert far not in result

  def test_results_sorted_by_distance_ascending(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    closer = LocationFactory(coord_lat=52.05, coord_lon=5.0)   # ~5 km
    farther = LocationFactory(coord_lat=52.2, coord_lon=5.0)   # ~22 km
    result = get_nearby_locations(home, radius_km=100)
    assert result.index(closer) < result.index(farther)

  def test_nearby_distance_attribute_is_set(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    LocationFactory(coord_lat=52.09, coord_lon=5.0)
    result = get_nearby_locations(home, radius_km=50)
    assert len(result) == 1
    assert hasattr(result[0], 'nearby_distance')
    assert isinstance(result[0].nearby_distance, float)

  def test_nearby_distance_is_rounded_to_one_decimal(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    LocationFactory(coord_lat=52.09, coord_lon=5.0)
    result = get_nearby_locations(home, radius_km=50)
    dist = result[0].nearby_distance
    assert dist == round(dist, 1)

  def test_excludes_locations_without_coordinates(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    no_coords = LocationFactory(coord_lat=None, coord_lon=None)
    result = get_nearby_locations(home, radius_km=10000)
    assert no_coords not in result

  def test_default_queryset_uses_published_only(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    draft = LocationFactory(coord_lat=52.09, coord_lon=5.0, status='c')
    result = get_nearby_locations(home, radius_km=50)
    assert draft not in result

  def test_custom_queryset_respected(self, db):
    from locations.models import Location
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    included = LocationFactory(coord_lat=52.09, coord_lon=5.0)
    excluded = LocationFactory(coord_lat=52.05, coord_lon=5.0)

    custom_qs = Location.objects.filter(pk=included.pk)
    result = get_nearby_locations(home, radius_km=50, queryset=custom_qs)

    assert included in result
    assert excluded not in result

  def test_custom_radius_respected(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    close = LocationFactory(coord_lat=52.09, coord_lon=5.0)   # ~10 km
    farther = LocationFactory(coord_lat=52.4, coord_lon=5.0)  # ~44 km

    result_small = get_nearby_locations(home, radius_km=20)
    result_large = get_nearby_locations(home, radius_km=100)

    assert close in result_small
    assert farther not in result_small
    assert farther in result_large

  def test_returns_list(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    result = get_nearby_locations(home, radius_km=50)
    assert isinstance(result, list)

  def test_multiple_nearby_locations(self, db):
    home = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    LocationFactory(coord_lat=52.05, coord_lon=5.0)
    LocationFactory(coord_lat=52.10, coord_lon=5.0)
    LocationFactory(coord_lat=52.15, coord_lon=5.0)
    result = get_nearby_locations(home, radius_km=50)
    assert len(result) == 3
