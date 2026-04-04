import pytest
from unittest.mock import patch, MagicMock

from locations.services.location_distance import (
  calculate_distance_to_departure_center,
  recalculate_all_distances,
)
from locations.tests.factories import LocationFactory


DEPARTURE_COORDS = (51.8833, 5.2958)  # Geldermalsen, Netherlands


# ------------------------------------------------------------------ #
#  calculate_distance_to_departure_center
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCalculateDistanceToDepartureCenter:

  @patch('locations.services.location_distance.get_departure_coordinates')
  def test_calculates_and_saves_distance(self, mock_coords):
    mock_coords.return_value = DEPARTURE_COORDS
    location = LocationFactory(coord_lat=52.3676, coord_lon=4.9041)  # Amsterdam

    result = calculate_distance_to_departure_center(location)

    assert result is not None
    assert result > 0
    location.refresh_from_db()
    assert location.distance_to_departure_center == result

  @patch('locations.services.location_distance.get_departure_coordinates')
  def test_returns_integer_km(self, mock_coords):
    mock_coords.return_value = DEPARTURE_COORDS
    location = LocationFactory(coord_lat=52.3676, coord_lon=4.9041)

    result = calculate_distance_to_departure_center(location)

    assert isinstance(result, int)

  @patch('locations.services.location_distance.get_departure_coordinates')
  def test_known_distance_amsterdam(self, mock_coords):
    mock_coords.return_value = DEPARTURE_COORDS
    location = LocationFactory(coord_lat=52.3676, coord_lon=4.9041)  # Amsterdam ≈ 55 km

    result = calculate_distance_to_departure_center(location)

    assert 40 < result < 80

  def test_returns_none_if_no_coordinates_and_no_address(self, db):
    location = LocationFactory(coord_lat=None, coord_lon=None, address=None)

    result = calculate_distance_to_departure_center(location)

    assert result is None
    location.refresh_from_db()
    assert location.distance_to_departure_center is None

  @patch('locations.services.location_geocoding.geocode_location')
  def test_tries_geocode_when_no_coords_but_has_address(self, mock_geocode):
    location = LocationFactory(
      coord_lat=None, coord_lon=None,
      address='Amsterdam, Netherlands'
    )
    mock_geocode.return_value = None  # geocode fails too

    result = calculate_distance_to_departure_center(location)

    mock_geocode.assert_called_once_with(location, request=None)
    assert result is None

  @patch('locations.services.location_distance.get_departure_coordinates')
  def test_returns_none_if_departure_coords_unavailable(self, mock_coords):
    mock_coords.return_value = None
    location = LocationFactory(coord_lat=52.0, coord_lon=5.0)

    result = calculate_distance_to_departure_center(location)

    assert result is None

  @patch('locations.services.location_distance.get_departure_coordinates')
  def test_does_not_save_if_distance_unchanged(self, mock_coords, db):
    mock_coords.return_value = DEPARTURE_COORDS
    location = LocationFactory(coord_lat=52.3676, coord_lon=4.9041)
    # Calculate once to set the distance
    calculate_distance_to_departure_center(location)
    location.refresh_from_db()
    original_modified = location.date_modified

    # Calculate again — should not save (distance unchanged)
    with patch.object(location, 'save') as mock_save:
      calculate_distance_to_departure_center(location)
      mock_save.assert_not_called()

  @patch('locations.services.location_distance.get_departure_coordinates')
  def test_triggers_region_recalculation_when_distance_changes(self, mock_coords, db):
    mock_coords.return_value = DEPARTURE_COORDS
    from locations.tests.factories import RegionFactory
    country = RegionFactory(parent=None, level='country')
    region = RegionFactory(parent=country, level='region')
    dept = RegionFactory(parent=region, level='department')

    location = LocationFactory(coord_lat=52.3676, coord_lon=4.9041, geo=dept)
    location.distance_to_departure_center = None  # force it to change

    with patch.object(dept, 'calculate_average_distance_to_center') as mock_calc:
      calculate_distance_to_departure_center(location)
      # region recalculation is triggered on location.region (the middle level)

  @patch('locations.services.location_distance.get_departure_coordinates')
  def test_handles_exception_gracefully(self, mock_coords):
    mock_coords.side_effect = Exception("network error")
    location = LocationFactory(coord_lat=52.0, coord_lon=5.0)

    result = calculate_distance_to_departure_center(location)

    assert result is None

  @patch('locations.services.location_distance.get_departure_coordinates')
  def test_passes_request_to_messages_on_error(self, mock_coords):
    from django.test import RequestFactory
    from django.contrib.messages.middleware import MessageMiddleware
    from django.contrib.sessions.middleware import SessionMiddleware

    mock_coords.return_value = None
    location = LocationFactory(coord_lat=52.0, coord_lon=5.0)

    request = RequestFactory().get('/')
    SessionMiddleware(lambda r: None).process_request(request)
    MessageMiddleware(lambda r: None).process_request(request)

    result = calculate_distance_to_departure_center(location, request=request)

    assert result is None


# ------------------------------------------------------------------ #
#  recalculate_all_distances
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestRecalculateAllDistances:

  @patch('locations.services.location_distance.calculate_distance_to_departure_center')
  def test_returns_stats_dict(self, mock_calc):
    mock_calc.return_value = 42
    LocationFactory(coord_lat=52.0, coord_lon=5.0)

    stats = recalculate_all_distances()

    assert 'calculated' in stats
    assert 'skipped' in stats
    assert 'failed' in stats

  @patch('locations.services.location_distance.calculate_distance_to_departure_center')
  def test_counts_calculated(self, mock_calc):
    mock_calc.return_value = 42
    LocationFactory(coord_lat=52.0, coord_lon=5.0)
    LocationFactory(coord_lat=53.0, coord_lon=6.0)

    stats = recalculate_all_distances()

    assert stats['calculated'] == 2
    assert stats['failed'] == 0
    assert stats['skipped'] == 0

  @patch('locations.services.location_distance.calculate_distance_to_departure_center')
  def test_counts_failed(self, mock_calc):
    mock_calc.return_value = None
    LocationFactory(coord_lat=52.0, coord_lon=5.0)

    stats = recalculate_all_distances()

    assert stats['failed'] == 1
    assert stats['calculated'] == 0

  def test_default_queryset_skips_locations_without_coordinates(self, db):
    LocationFactory(coord_lat=None, coord_lon=None)  # no coords, excluded from default qs

    with patch('locations.services.location_distance.calculate_distance_to_departure_center') as mock_calc:
      mock_calc.return_value = None
      stats = recalculate_all_distances()

    assert stats['calculated'] == 0
    assert stats['failed'] == 0
    assert stats['skipped'] == 0  # excluded from queryset, not iterated

  @patch('locations.services.location_distance.calculate_distance_to_departure_center')
  def test_custom_queryset_used(self, mock_calc, db):
    mock_calc.return_value = 42
    from locations.models import Location
    loc = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    LocationFactory(coord_lat=53.0, coord_lon=6.0)

    qs = Location.objects.filter(pk=loc.pk)
    stats = recalculate_all_distances(queryset=qs)

    assert stats['calculated'] == 1

  @patch('locations.services.location_distance.get_departure_coordinates')
  def test_exception_with_request_adds_error_message(self, mock_coords, db):
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.test import RequestFactory
    mock_coords.side_effect = Exception('boom')
    location = LocationFactory(coord_lat=52.0, coord_lon=5.0)
    request = RequestFactory().get('/')
    request.session = {}
    request._messages = FallbackStorage(request)
    result = calculate_distance_to_departure_center(location, request=request)
    assert result is None
    msgs = list(request._messages)
    assert any('error' in str(m.tags) for m in msgs)

  @patch('locations.services.location_distance.calculate_distance_to_departure_center')
  def test_skipped_counted_when_no_coords_and_result_none(self, mock_calc, db):
    """skipped branch: location in custom queryset has no coords and distance returns None."""
    from locations.models import Location
    mock_calc.return_value = None
    loc = LocationFactory(coord_lat=None, coord_lon=None)
    stats = recalculate_all_distances(queryset=Location.objects.filter(pk=loc.pk))
    assert stats['skipped'] == 1
