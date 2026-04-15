import pytest
from unittest.mock import patch, MagicMock
from geopy.exc import GeocoderQueryError

from locations.services.location_geocoding import (
  geocode_location,
  geocode_multiple_locations,
  fetch_address,
  fetch_phone,
  fetch_place_id,
  enrich_location,
  resolve_geo,
  _geocode_raw,
  _extract_address_parts,
  _geocode_result_has_street,
  _address_is_hint,
  _google_address_is_richer,
  _seed_types_from_google,
)
from locations.tests.factories import LocationFactory, RegionFactory


def _make_request():
  from django.test import RequestFactory
  from django.contrib.auth.models import AnonymousUser
  from django.contrib.messages.middleware import MessageMiddleware
  from django.contrib.sessions.middleware import SessionMiddleware
  request = RequestFactory().get('/')
  request.user = AnonymousUser()
  SessionMiddleware(lambda r: None).process_request(request)
  MessageMiddleware(lambda r: None).process_request(request)
  return request


def _make_geocode_result(
  lat=52.37, lon=4.90,
  place_id='ChIJtest',
  address='Teststraat 1, 1234 AB Amsterdam, Netherlands',
  address_components=None,
  types=None,
):
  result = MagicMock()
  result.latitude = lat
  result.longitude = lon
  result.address = address
  result.raw = {
    'place_id': place_id,
    'types': types or ['establishment'],
    'address_components': address_components or [
      {'types': ['street_number'],              'long_name': '1',           'short_name': '1'},
      {'types': ['country'],                    'long_name': 'Netherlands', 'short_name': 'NL'},
      {'types': ['administrative_area_level_1'],'long_name': 'North Holland','short_name': 'NH'},
      {'types': ['administrative_area_level_2'],'long_name': 'Amsterdam',   'short_name': 'Amsterdam'},
    ],
  }
  return result


def _mock_geocode_result(lat=52.3676, lon=4.9041):
  """Return a fake geopy Location result."""
  result = MagicMock()
  result.latitude = lat
  result.longitude = lon
  return result


# ------------------------------------------------------------------ #
#  geocode_location
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGeocodeLocation:

  def test_returns_none_if_no_address(self, db):
    location = LocationFactory(address=None)
    result = geocode_location(location)
    assert result is None

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_returns_lat_lon_tuple_on_success(self, mock_v3):
    mock_v3.return_value.geocode.return_value = _mock_geocode_result(52.37, 4.90)
    location = LocationFactory(address='Amsterdam, Netherlands')

    result = geocode_location(location)

    assert result == (52.37, 4.90)

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_saves_coordinates_to_location(self, mock_v3):
    mock_v3.return_value.geocode.return_value = _mock_geocode_result(52.37, 4.90)
    location = LocationFactory(address='Amsterdam, Netherlands', coord_lat=None, coord_lon=None)

    geocode_location(location)

    location.refresh_from_db()
    assert float(location.coord_lat) == 52.37
    assert float(location.coord_lon) == 4.90

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_returns_none_if_geocoder_returns_no_result(self, mock_v3):
    mock_v3.return_value.geocode.return_value = None
    location = LocationFactory(address='Nowhere Land 99999')

    result = geocode_location(location)

    assert result is None

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_returns_none_on_geocoder_query_error(self, mock_v3):
    mock_v3.return_value.geocode.side_effect = GeocoderQueryError("invalid key")
    location = LocationFactory(address='Amsterdam, Netherlands')

    result = geocode_location(location)

    assert result is None

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_adds_success_message_when_request_provided(self, mock_v3):
    from django.test import RequestFactory
    from django.contrib.messages.middleware import MessageMiddleware
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.messages import get_messages

    mock_v3.return_value.geocode.return_value = _mock_geocode_result(52.37, 4.90)
    location = LocationFactory(address='Amsterdam, Netherlands')

    request = RequestFactory().get('/')
    SessionMiddleware(lambda r: None).process_request(request)
    MessageMiddleware(lambda r: None).process_request(request)

    geocode_location(location, request=request)

    msgs = list(get_messages(request))
    assert any('52.37' in str(m) or location.name in str(m) for m in msgs)

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_adds_warning_message_when_no_result_and_request_provided(self, mock_v3):
    from django.test import RequestFactory
    from django.contrib.messages.middleware import MessageMiddleware
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.messages import get_messages

    mock_v3.return_value.geocode.return_value = None
    location = LocationFactory(address='Nowhere Land')

    request = RequestFactory().get('/')
    SessionMiddleware(lambda r: None).process_request(request)
    MessageMiddleware(lambda r: None).process_request(request)

    geocode_location(location, request=request)

    msgs = list(get_messages(request))
    assert len(msgs) == 1

  def test_adds_warning_when_no_address_and_request_provided(self, db):
    from django.test import RequestFactory
    from django.contrib.messages.middleware import MessageMiddleware
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.messages import get_messages

    location = LocationFactory(address=None)

    request = RequestFactory().get('/')
    SessionMiddleware(lambda r: None).process_request(request)
    MessageMiddleware(lambda r: None).process_request(request)

    result = geocode_location(location, request=request)

    assert result is None
    msgs = list(get_messages(request))
    assert len(msgs) == 1

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_does_not_raise_on_geocoder_error_without_request(self, mock_v3):
    mock_v3.return_value.geocode.side_effect = GeocoderQueryError("error")
    location = LocationFactory(address='Amsterdam')

    result = geocode_location(location)  # should not raise

    assert result is None


# ------------------------------------------------------------------ #
#  geocode_multiple_locations
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGeocodeMultipleLocations:

  @patch('locations.services.location_geocoding.geocode_location')
  def test_returns_stats_dict(self, mock_geocode):
    mock_geocode.return_value = (52.0, 5.0)
    from locations.models import Location
    LocationFactory(address='Amsterdam', coord_lat=None, coord_lon=None)

    stats = geocode_multiple_locations(Location.objects.all())

    assert 'success' in stats
    assert 'failed' in stats
    assert 'skipped' in stats

  @patch('locations.services.location_geocoding.geocode_location')
  def test_counts_success(self, mock_geocode):
    mock_geocode.return_value = (52.0, 5.0)
    from locations.models import Location
    LocationFactory(address='Amsterdam', coord_lat=None, coord_lon=None)
    LocationFactory(address='Utrecht', coord_lat=None, coord_lon=None)

    stats = geocode_multiple_locations(Location.objects.all())

    assert stats['success'] == 2
    assert stats['failed'] == 0

  @patch('locations.services.location_geocoding.geocode_location')
  def test_counts_failed(self, mock_geocode):
    mock_geocode.return_value = None
    from locations.models import Location
    LocationFactory(address='Nowhere', coord_lat=None, coord_lon=None)

    stats = geocode_multiple_locations(Location.objects.all())

    assert stats['failed'] == 1
    assert stats['success'] == 0

  def test_skips_locations_already_geocoded(self, db):
    from locations.models import Location
    # Location already has coordinates — should not be included in batch
    LocationFactory(address='Amsterdam', coord_lat=52.37, coord_lon=4.90)

    with patch('locations.services.location_geocoding.geocode_location') as mock_geocode:
      geocode_multiple_locations(Location.objects.all())
      mock_geocode.assert_not_called()

  def test_skips_locations_without_address(self, db):
    from locations.models import Location
    LocationFactory(address=None, coord_lat=None, coord_lon=None)
    LocationFactory(address='', coord_lat=None, coord_lon=None)

    with patch('locations.services.location_geocoding.geocode_location') as mock_geocode:
      geocode_multiple_locations(Location.objects.all())
      mock_geocode.assert_not_called()

  @patch('locations.services.location_geocoding.geocode_location')
  def test_mixed_success_and_failure(self, mock_geocode):
    from locations.models import Location
    LocationFactory(address='Amsterdam', coord_lat=None, coord_lon=None)
    LocationFactory(address='Nowhere', coord_lat=None, coord_lon=None)

    mock_geocode.side_effect = [(52.0, 5.0), None]

    stats = geocode_multiple_locations(Location.objects.all())

    assert stats['success'] == 1
    assert stats['failed'] == 1


# ------------------------------------------------------------------ #
#  _geocode_raw — error branches
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGeocodeRaw:

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_query_error_with_request_adds_message(self, mock_v3):
    mock_v3.return_value.geocode.side_effect = GeocoderQueryError("bad key")
    location = LocationFactory(address='Amsterdam')
    request = _make_request()

    result = _geocode_raw(location, request=request)

    from django.contrib.messages import get_messages
    assert result is None
    msgs = list(get_messages(request))
    assert len(msgs) == 1

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_generic_exception_without_request_returns_none(self, mock_v3):
    mock_v3.return_value.geocode.side_effect = RuntimeError("network down")
    location = LocationFactory(address='Amsterdam')

    result = _geocode_raw(location)

    assert result is None

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_generic_exception_with_request_adds_message(self, mock_v3):
    mock_v3.return_value.geocode.side_effect = RuntimeError("network down")
    location = LocationFactory(address='Amsterdam')
    request = _make_request()

    result = _geocode_raw(location, request=request)

    from django.contrib.messages import get_messages
    assert result is None
    assert len(list(get_messages(request))) == 1

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_address_hint_used_instead_of_location_address(self, mock_v3):
    mock_v3.return_value.geocode.return_value = _make_geocode_result()
    location = LocationFactory(address=None)

    result = _geocode_raw(location, address_hint='france')

    assert result is not None
    call_arg = mock_v3.return_value.geocode.call_args[0][0]
    assert 'france' in call_arg


# ------------------------------------------------------------------ #
#  fetch_address
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestFetchAddress:

  def test_returns_existing_address_without_api_call(self, db):
    location = LocationFactory(address='Already set')

    with patch('locations.services.location_geocoding.GoogleV3') as mock_v3:
      result = fetch_address(location)

    mock_v3.assert_not_called()
    assert result == 'Already set'

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_saves_address_on_success(self, mock_v3):
    geo_result = MagicMock()
    geo_result.address = 'Teststraat 1, Amsterdam, Netherlands'
    mock_v3.return_value.geocode.return_value = geo_result
    location = LocationFactory(address=None)

    result = fetch_address(location)

    location.refresh_from_db()
    assert result == 'Teststraat 1, Amsterdam, Netherlands'
    assert location.address == 'Teststraat 1, Amsterdam, Netherlands'

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_returns_none_when_no_result(self, mock_v3):
    mock_v3.return_value.geocode.return_value = None
    location = LocationFactory(address=None)

    result = fetch_address(location)

    assert result is None

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_no_result_with_request_adds_warning(self, mock_v3):
    from django.contrib.messages import get_messages
    mock_v3.return_value.geocode.return_value = None
    location = LocationFactory(address=None)
    request = _make_request()

    fetch_address(location, request=request)

    msgs = list(get_messages(request))
    assert len(msgs) == 1

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_query_error_returns_none(self, mock_v3):
    mock_v3.return_value.geocode.side_effect = GeocoderQueryError("bad")
    location = LocationFactory(address=None)

    result = fetch_address(location)

    assert result is None

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_query_error_with_request_adds_message(self, mock_v3):
    from django.contrib.messages import get_messages
    mock_v3.return_value.geocode.side_effect = GeocoderQueryError("bad")
    location = LocationFactory(address=None)
    request = _make_request()

    fetch_address(location, request=request)

    assert len(list(get_messages(request))) == 1

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_generic_exception_returns_none(self, mock_v3):
    mock_v3.return_value.geocode.side_effect = RuntimeError("boom")
    location = LocationFactory(address=None)

    result = fetch_address(location)

    assert result is None

  @patch('locations.services.location_geocoding.GoogleV3')
  def test_success_with_request_adds_info_message(self, mock_v3):
    from django.contrib.messages import get_messages
    geo_result = MagicMock()
    geo_result.address = 'Found St 1, Amsterdam'
    mock_v3.return_value.geocode.return_value = geo_result
    location = LocationFactory(address=None)
    request = _make_request()

    fetch_address(location, request=request)

    assert len(list(get_messages(request))) == 1


# ------------------------------------------------------------------ #
#  _extract_address_parts
# ------------------------------------------------------------------ #

class TestExtractAddressParts:

  def test_raises_on_empty_components(self):
    result = MagicMock()
    result.raw = {'address_components': []}

    with pytest.raises(ValueError, match='no address_components'):
      _extract_address_parts(result)

  def test_raises_when_country_missing(self):
    result = MagicMock()
    result.raw = {'address_components': [
      {'types': ['administrative_area_level_1'], 'long_name': 'Noord-Holland', 'short_name': 'NH'},
    ]}

    with pytest.raises(ValueError):
      _extract_address_parts(result)

  def test_returns_country_region_department(self):
    result = _make_geocode_result()

    parts = _extract_address_parts(result)

    assert parts['country'] == 'Netherlands'
    assert parts['region'] == 'North Holland'
    assert parts['department'] == 'Amsterdam'

  def test_locality_used_as_department_fallback(self):
    result = MagicMock()
    result.raw = {'address_components': [
      {'types': ['country'],                    'long_name': 'France',      'short_name': 'FR'},
      {'types': ['administrative_area_level_1'],'long_name': 'Île-de-France','short_name': 'IDF'},
      {'types': ['locality'],                   'long_name': 'Paris',       'short_name': 'Paris'},
    ]}

    parts = _extract_address_parts(result)

    assert parts['department'] == 'Paris'

  def test_admin_level_2_beats_locality_for_department(self):
    """When both administrative_area_level_2 and locality are present,
    MAPPING priority must win — admin_level_2 should be used as department,
    not the locality (regression test for French addresses like Mama Café / Lot)."""
    result = MagicMock()
    result.raw = {'address_components': [
      {'types': ['country'],                     'long_name': 'France',    'short_name': 'FR'},
      {'types': ['administrative_area_level_1'], 'long_name': 'Occitanie', 'short_name': 'OCC'},
      {'types': ['locality'],                    'long_name': 'Saint-Céré','short_name': 'Saint-Céré'},
      {'types': ['administrative_area_level_2'], 'long_name': 'Lot',       'short_name': 'Lot'},
    ]}

    parts = _extract_address_parts(result)

    assert parts['department'] == 'Lot'
    assert parts['region'] == 'Occitanie'

  def test_sublocality_overrides_admin_level1_for_region(self):
    result = MagicMock()
    result.raw = {'address_components': [
      {'types': ['country'],             'long_name': 'France',   'short_name': 'FR'},
      {'types': ['sublocality_level_1'], 'long_name': 'Le Marais','short_name': 'LM'},
    ]}

    parts = _extract_address_parts(result)

    assert parts['region'] == 'Le Marais'


# ------------------------------------------------------------------ #
#  resolve_geo
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestResolveGeo:

  def test_creates_region_hierarchy_and_sets_geo(self, db):
    location = LocationFactory()
    geocode_result = _make_geocode_result()

    dept = resolve_geo(location, geocode_result)

    location.refresh_from_db()
    assert dept is not None
    assert location.geo == dept
    assert dept.name == 'Amsterdam'
    assert dept.parent.name == 'North Holland'
    assert dept.parent.parent.name == 'Netherlands'

  def test_returns_none_on_invalid_components(self, db):
    location = LocationFactory()
    geocode_result = MagicMock()
    geocode_result.raw = {'address_components': []}

    result = resolve_geo(location, geocode_result)

    assert result is None

  def test_returns_none_with_request_adds_warning(self, db):
    from django.contrib.messages import get_messages
    location = LocationFactory()
    geocode_result = MagicMock()
    geocode_result.raw = {'address_components': []}
    request = _make_request()

    result = resolve_geo(location, geocode_result, request=request)

    assert result is None
    assert len(list(get_messages(request))) == 1

  def test_reuses_existing_region_objects(self, db):
    from locations.models.Region import Region
    country = RegionFactory(slug='nl', name='Netherlands', parent=None)
    region = RegionFactory(slug='nh', name='North Holland', parent=country)
    RegionFactory(slug='amsterdam', name='Amsterdam', parent=region)
    location = LocationFactory()
    geocode_result = _make_geocode_result(address_components=[
      {'types': ['country'],                    'long_name': 'Netherlands',  'short_name': 'NL'},
      {'types': ['administrative_area_level_1'],'long_name': 'North Holland','short_name': 'NH'},
      {'types': ['administrative_area_level_2'],'long_name': 'Amsterdam',    'short_name': 'Amsterdam'},
    ])

    resolve_geo(location, geocode_result)

    assert Region.objects.count() == 3  # no duplicates created

  def test_success_with_request_adds_info_message(self, db):
    from django.contrib.messages import get_messages
    location = LocationFactory()
    geocode_result = _make_geocode_result()
    request = _make_request()

    resolve_geo(location, geocode_result, request=request)

    assert len(list(get_messages(request))) == 1


# ------------------------------------------------------------------ #
#  helper functions
# ------------------------------------------------------------------ #

class TestGeocodeHelpers:

  def test_has_street_number_returns_true(self):
    result = MagicMock()
    result.raw = {'address_components': [
      {'types': ['street_number'], 'long_name': '1', 'short_name': '1'},
    ]}
    assert _geocode_result_has_street(result) is True

  def test_no_street_number_returns_false(self):
    result = MagicMock()
    result.raw = {'address_components': [
      {'types': ['country'], 'long_name': 'Netherlands', 'short_name': 'NL'},
    ]}
    assert _geocode_result_has_street(result) is False

  def test_address_is_hint_no_digits(self):
    assert _address_is_hint('france') is True
    assert _address_is_hint('Gelderland') is True

  def test_address_is_hint_has_digits(self):
    assert _address_is_hint('Rijksstraatweg 1') is False
    assert _address_is_hint('75001 Paris') is False

  def test_address_is_hint_none(self):
    assert _address_is_hint(None) is True

  def test_google_address_is_richer_no_user_address(self):
    assert _google_address_is_richer(None, 'Some long Google address') is True

  def test_google_address_is_richer_long_enough(self):
    assert _google_address_is_richer('france', 'Rijksstraatweg 1, 6744 PH Ederveen, Netherlands') is True

  def test_google_address_is_richer_not_long_enough(self):
    assert _google_address_is_richer('Amsterdam city', 'Amsterdam') is False


# ------------------------------------------------------------------ #
#  _seed_types_from_google
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestSeedTypesFromGoogle:

  def test_skips_when_categories_exist(self, db):
    from locations.tests.factories import CategoryFactory
    location = LocationFactory()
    cat = CategoryFactory(status='p')
    location.categories.add(cat)

    result = MagicMock()
    result.raw = {'types': ['campground']}

    location.is_accommodation = False
    _seed_types_from_google(location, result)

    assert location.is_accommodation is False  # unchanged

  def test_sets_accommodation_from_google_type(self, db):
    location = LocationFactory()
    result = MagicMock()
    result.raw = {'types': ['campground']}

    _seed_types_from_google(location, result)

    assert location.is_accommodation is True
    assert location.is_activity is False

  def test_sets_activity_from_google_type(self, db):
    location = LocationFactory()
    result = MagicMock()
    result.raw = {'types': ['museum']}

    _seed_types_from_google(location, result)

    assert location.is_activity is True
    assert location.is_accommodation is False

  def test_sets_both_when_both_types_present(self, db):
    location = LocationFactory()
    result = MagicMock()
    result.raw = {'types': ['campground', 'tourist_attraction']}

    _seed_types_from_google(location, result)

    assert location.is_accommodation is True
    assert location.is_activity is True

  def test_falls_back_to_accommodation_when_unknown_types(self, db):
    location = LocationFactory()
    result = MagicMock()
    result.raw = {'types': ['point_of_interest', 'establishment']}

    _seed_types_from_google(location, result)

    assert location.is_accommodation is True
    assert location.is_activity is False


# ------------------------------------------------------------------ #
#  fetch_phone
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestFetchPhone:

  def test_returns_existing_phone_without_api_call(self, db):
    location = LocationFactory()
    location.phone = '+31 20 123 4567'

    with patch('locations.services.location_geocoding._get_gmaps_client') as mock_gmaps:
      result = fetch_phone(location)

    mock_gmaps.assert_not_called()
    assert result == '+31 20 123 4567'

  def test_returns_none_when_no_place_id(self, db):
    location = LocationFactory()
    location.google_place_id = None
    location.phone = None

    with patch('locations.services.location_geocoding._get_gmaps_client') as mock_gmaps:
      result = fetch_phone(location)

    mock_gmaps.assert_not_called()
    assert result is None

  @patch('locations.services.location_geocoding._get_gmaps_client')
  def test_saves_formatted_phone_on_success(self, mock_gmaps_fn):
    mock_gmaps_fn.return_value.place.return_value = {
      'result': {'formatted_phone_number': '+31 20 123 4567'},
    }
    location = LocationFactory()
    location.phone = None
    location.google_place_id = 'ChIJtest'
    location.save(update_fields=['phone', 'google_place_id'])

    result = fetch_phone(location)

    location.refresh_from_db()
    assert result == '+31 20 123 4567'
    assert location.phone == '+31 20 123 4567'

  @patch('locations.services.location_geocoding._get_gmaps_client')
  def test_falls_back_to_international_phone(self, mock_gmaps_fn):
    mock_gmaps_fn.return_value.place.return_value = {
      'result': {'international_phone_number': '+31 20 123 4567'},
    }
    location = LocationFactory()
    location.phone = None
    location.google_place_id = 'ChIJtest'
    location.save(update_fields=['phone', 'google_place_id'])

    result = fetch_phone(location)

    assert result == '+31 20 123 4567'

  @patch('locations.services.location_geocoding._get_gmaps_client')
  def test_returns_none_when_no_phone_in_result(self, mock_gmaps_fn):
    mock_gmaps_fn.return_value.place.return_value = {'result': {}}
    location = LocationFactory()
    location.phone = None
    location.google_place_id = 'ChIJtest'
    location.save(update_fields=['phone', 'google_place_id'])

    result = fetch_phone(location)

    assert result is None

  @patch('locations.services.location_geocoding._get_gmaps_client')
  def test_returns_none_on_api_exception(self, mock_gmaps_fn):
    mock_gmaps_fn.return_value.place.side_effect = Exception("API error")
    location = LocationFactory()
    location.phone = None
    location.google_place_id = 'ChIJtest'
    location.save(update_fields=['phone', 'google_place_id'])

    result = fetch_phone(location)

    assert result is None


# ------------------------------------------------------------------ #
#  fetch_place_id
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestFetchPlaceId:

  def test_returns_existing_place_id_without_geocoding(self, db):
    location = LocationFactory()
    location.google_place_id = 'ChIJexisting'
    location.save(update_fields=['google_place_id'])

    with patch('locations.services.location_geocoding._geocode_raw') as mock_raw:
      result = fetch_place_id(location)

    mock_raw.assert_not_called()
    assert result == 'ChIJexisting'

  @patch('locations.services.location_geocoding._geocode_raw')
  def test_returns_none_when_geocode_fails(self, mock_raw):
    mock_raw.return_value = None
    location = LocationFactory(address='Amsterdam')
    location.google_place_id = None
    location.save(update_fields=['google_place_id'])

    result = fetch_place_id(location)

    assert result is None

  @patch('locations.services.location_geocoding._geocode_raw')
  def test_saves_place_id_on_success(self, mock_raw):
    geo_result = MagicMock()
    geo_result.raw = {'place_id': 'ChIJnew'}
    mock_raw.return_value = geo_result
    location = LocationFactory(address='Amsterdam')
    location.google_place_id = None
    location.save(update_fields=['google_place_id'])

    result = fetch_place_id(location)

    location.refresh_from_db()
    assert result == 'ChIJnew'
    assert location.google_place_id == 'ChIJnew'

  @patch('locations.services.location_geocoding._geocode_raw')
  def test_returns_none_when_no_place_id_in_result(self, mock_raw):
    geo_result = MagicMock()
    geo_result.raw = {}
    mock_raw.return_value = geo_result
    location = LocationFactory(address='Amsterdam')
    location.google_place_id = None
    location.save(update_fields=['google_place_id'])

    result = fetch_place_id(location)

    assert result is None


# ------------------------------------------------------------------ #
#  enrich_location
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestEnrichLocation:

  @patch('locations.services.location_geocoding.fetch_address')
  @patch('locations.services.location_geocoding._geocode_raw')
  def test_calls_fetch_address_when_no_address_and_no_hint(self, mock_raw, mock_fetch):
    mock_raw.return_value = None
    location = LocationFactory(address=None)

    enrich_location(location)

    mock_fetch.assert_called_once_with(location, request=None)

  @patch('locations.services.location_geocoding.fetch_address')
  @patch('locations.services.location_geocoding._geocode_raw')
  def test_skips_fetch_address_when_hint_provided(self, mock_raw, mock_fetch):
    mock_raw.return_value = None
    location = LocationFactory(address=None)

    enrich_location(location, address_hint='france')

    mock_fetch.assert_not_called()

  @patch('locations.services.location_geocoding._geocode_raw')
  def test_returns_early_when_geocode_fails(self, mock_raw):
    mock_raw.return_value = None
    location = LocationFactory(address='Amsterdam')

    with patch('locations.services.location_geocoding.resolve_geo') as mock_resolve:
      enrich_location(location)
      mock_resolve.assert_not_called()

  @patch('locations.services.location_geocoding.resolve_geo')
  @patch('locations.services.location_geocoding.fetch_phone')
  @patch('locations.services.location_geocoding._geocode_raw')
  def test_saves_coordinates(self, mock_raw, mock_phone, mock_resolve):
    mock_raw.return_value = _make_geocode_result(lat=48.85, lon=2.35)
    location = LocationFactory(address='Paris, France', coord_lat=None, coord_lon=None)

    enrich_location(location)

    location.refresh_from_db()
    assert float(location.coord_lat) == 48.85
    assert float(location.coord_lon) == 2.35

  @patch('locations.services.location_geocoding.resolve_geo')
  @patch('locations.services.location_geocoding.fetch_phone')
  @patch('locations.services.location_geocoding._geocode_raw')
  def test_stores_place_id(self, mock_raw, mock_phone, mock_resolve):
    mock_raw.return_value = _make_geocode_result(place_id='ChIJstored')
    location = LocationFactory(address='Paris, France')
    location.google_place_id = None
    location.save(update_fields=['google_place_id'])

    enrich_location(location)

    location.refresh_from_db()
    assert location.google_place_id == 'ChIJstored'

  @patch('locations.services.location_geocoding.resolve_geo')
  @patch('locations.services.location_geocoding.fetch_phone')
  @patch('locations.services.location_geocoding._geocode_raw')
  def test_does_not_overwrite_existing_place_id(self, mock_raw, mock_phone, mock_resolve):
    mock_raw.return_value = _make_geocode_result(place_id='ChIJnew')
    location = LocationFactory(address='Paris, France')
    location.google_place_id = 'ChIJoriginal'
    location.save(update_fields=['google_place_id'])

    enrich_location(location)

    location.refresh_from_db()
    assert location.google_place_id == 'ChIJoriginal'

  @patch('locations.services.location_geocoding.resolve_geo')
  @patch('locations.services.location_geocoding.fetch_phone')
  @patch('locations.services.location_geocoding._geocode_raw')
  def test_updates_hint_address_with_richer_google_address(self, mock_raw, mock_phone, mock_resolve):
    mock_raw.return_value = _make_geocode_result(
      address='Rijksstraatweg 1, 6744 PH Ederveen, Netherlands',
    )
    location = LocationFactory(address=None)

    enrich_location(location, address_hint='nederland')

    location.refresh_from_db()
    assert location.address == 'Rijksstraatweg 1, 6744 PH Ederveen, Netherlands'

  @patch('locations.services.location_geocoding.resolve_geo')
  @patch('locations.services.location_geocoding.fetch_phone')
  @patch('locations.services.location_geocoding._geocode_raw')
  def test_calls_resolve_geo(self, mock_raw, mock_phone, mock_resolve):
    geo_result = _make_geocode_result()
    mock_raw.return_value = geo_result
    location = LocationFactory(address='Amsterdam')

    enrich_location(location)

    mock_resolve.assert_called_once_with(location, geo_result, request=None)

  @patch('locations.services.location_geocoding.resolve_geo')
  @patch('locations.services.location_geocoding.fetch_phone')
  @patch('locations.services.location_geocoding._geocode_raw')
  def test_calls_fetch_phone_when_place_id_set(self, mock_raw, mock_phone, mock_resolve):
    mock_raw.return_value = _make_geocode_result(place_id='ChIJtest')
    location = LocationFactory(address='Amsterdam')
    location.google_place_id = None
    location.phone = None
    location.save(update_fields=['google_place_id', 'phone'])

    enrich_location(location)

    mock_phone.assert_called_once()

  @patch('locations.services.location_geocoding.resolve_geo')
  @patch('locations.services.location_geocoding.fetch_phone')
  @patch('locations.services.location_geocoding._geocode_raw')
  def test_skips_fetch_phone_when_phone_already_set(self, mock_raw, mock_phone, mock_resolve):
    mock_raw.return_value = _make_geocode_result(place_id='ChIJtest')
    location = LocationFactory(address='Amsterdam')
    location.phone = '+31 20 000 0000'
    location.google_place_id = 'ChIJtest'
    location.save(update_fields=['phone', 'google_place_id'])

    enrich_location(location)

    mock_phone.assert_not_called()

  @patch('locations.services.location_geocoding.resolve_geo')
  @patch('locations.services.location_geocoding.fetch_phone')
  @patch('locations.services.location_geocoding._geocode_raw')
  def test_success_with_request_adds_message(self, mock_raw, mock_phone, mock_resolve):
    from django.contrib.messages import get_messages
    mock_raw.return_value = _make_geocode_result()
    location = LocationFactory(address='Amsterdam')
    request = _make_request()

    enrich_location(location, request=request)

    assert len(list(get_messages(request))) >= 1


# ------------------------------------------------------------------ #
#  Coverage gaps
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGeocodingCoverageGaps:

  def test_get_gmaps_client_returns_client(self):
    """Line 28 — _get_gmaps_client() returns a googlemaps Client."""
    from locations.services.location_geocoding import _get_gmaps_client
    with patch('locations.services.location_geocoding.googlemaps') as mock_gm:
      mock_gm.Client.return_value = 'client'
      result = _get_gmaps_client()
    assert result == 'client'

  @patch('locations.services.location_geocoding._get_geolocator')
  def test_geocode_raw_unexpected_exception_with_request_adds_message(self, mock_geo):
    """Line 66 — unexpected exception path in _geocode_raw with request."""
    mock_geo.return_value.geocode.side_effect = RuntimeError('unexpected')
    location = LocationFactory()
    request = _make_request()
    result = _geocode_raw(location, request=request)
    assert result is None
    from django.contrib.messages import get_messages
    assert len(list(get_messages(request))) >= 1

  @patch('locations.services.location_geocoding._get_geolocator')
  def test_fetch_address_unexpected_exception_with_request_adds_message(self, mock_geo):
    """Lines 110, 112 — unexpected exception in fetch_address with request."""
    mock_geo.return_value.geocode.side_effect = RuntimeError('oops')
    location = LocationFactory(address=None)
    request = _make_request()
    result = fetch_address(location, request=request)
    assert result is None
    from django.contrib.messages import get_messages
    assert len(list(get_messages(request))) >= 1

  def test_extract_address_parts_debug_prints_missing_fields(self, capsys):
    """Lines 209-211 — DEBUG=True branch logs missing address fields."""
    from unittest.mock import MagicMock
    from locations.services.location_geocoding import _extract_address_parts
    geocode_result = MagicMock()
    geocode_result.raw = {'address_components': []}  # empty → all fields missing
    with patch('locations.services.location_geocoding.settings') as mock_settings:
      mock_settings.DEBUG = True
      try:
        _extract_address_parts(geocode_result)
      except ValueError:
        pass  # expected — no address_components raises ValueError
    captured = capsys.readouterr()
    # Empty components raises before the debug print — use a component with no mapping
    # to reach the debug print. Pass a component that fills nothing useful.
    geocode_result.raw = {'address_components': [
      {'types': ['premise'], 'long_name': 'A', 'short_name': 'A'}
    ]}
    with patch('locations.services.location_geocoding.settings') as mock_settings:
      mock_settings.DEBUG = True
      try:
        _extract_address_parts(geocode_result)
      except ValueError:
        pass
    captured = capsys.readouterr()
    assert 'Missing address fields' in captured.out

  @patch('locations.services.location_geocoding._get_geolocator')
  def test_geocode_raw_unexpected_exception_debug_appends_detail(self, mock_geo):
    """Line 66 — DEBUG=True appends exception detail to message."""
    from django.test import override_settings
    mock_geo.return_value.geocode.side_effect = RuntimeError('boom detail')
    location = LocationFactory(address='Amsterdam, Netherlands')
    request = _make_request()
    with override_settings(DEBUG=True):
      _geocode_raw(location, request=request)
    from django.contrib.messages import get_messages
    msgs = [str(m) for m in get_messages(request)]
    assert any('boom detail' in m for m in msgs)

  @patch('locations.services.location_geocoding._get_geolocator')
  def test_fetch_address_unexpected_exception_debug_appends_detail(self, mock_geo):
    """Line 110 — DEBUG=True appends exception detail to message."""
    from django.test import override_settings
    mock_geo.return_value.geocode.side_effect = RuntimeError('addr detail')
    location = LocationFactory(address=None)
    request = _make_request()
    with override_settings(DEBUG=True):
      fetch_address(location, request=request)
    from django.contrib.messages import get_messages
    msgs = [str(m) for m in get_messages(request)]
    assert any('addr detail' in m for m in msgs)
