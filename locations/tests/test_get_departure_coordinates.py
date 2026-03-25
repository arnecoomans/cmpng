import pytest
from unittest.mock import patch, MagicMock

from locations.utils.get_departure_coordinates import get_departure_coordinates


# ------------------------------------------------------------------ #
#  get_departure_coordinates
# ------------------------------------------------------------------ #

class TestGetDepartureCoordinates:

    def test_returns_cached_coords_without_geocoding(self, settings):
        settings.DEPARTURE_CENTER = 'Geldermalsen, Netherlands'
        cached = (51.878, 5.289)

        with patch('locations.utils.get_departure_coordinates.cache') as mock_cache:
            mock_cache.get.return_value = cached
            result = get_departure_coordinates()

        assert result == cached
        mock_cache.get.assert_called_once()

    def test_geocodes_on_cache_miss_and_caches_result(self, settings):
        settings.DEPARTURE_CENTER = 'Geldermalsen, Netherlands'
        settings.GOOGLE_API_KEY = 'fake-key'

        fake_location = MagicMock()
        fake_location.latitude = 51.878
        fake_location.longitude = 5.289

        with patch('locations.utils.get_departure_coordinates.cache') as mock_cache, \
             patch('locations.utils.get_departure_coordinates.GoogleV3') as MockGeocoder:
            mock_cache.get.return_value = None
            MockGeocoder.return_value.geocode.return_value = fake_location

            result = get_departure_coordinates()

        assert result == (51.878, 5.289)
        mock_cache.set.assert_called_once()
        # Verify 30-day TTL
        _, _, ttl = mock_cache.set.call_args[0]
        assert ttl == 60 * 60 * 24 * 30

    def test_returns_none_when_geocoder_returns_nothing(self, settings):
        settings.DEPARTURE_CENTER = 'Geldermalsen, Netherlands'
        settings.GOOGLE_API_KEY = 'fake-key'

        with patch('locations.utils.get_departure_coordinates.cache') as mock_cache, \
             patch('locations.utils.get_departure_coordinates.GoogleV3') as MockGeocoder:
            mock_cache.get.return_value = None
            MockGeocoder.return_value.geocode.return_value = None

            result = get_departure_coordinates()

        assert result is None

    def test_returns_none_when_geocoder_raises(self, settings):
        settings.DEPARTURE_CENTER = 'Geldermalsen, Netherlands'
        settings.GOOGLE_API_KEY = 'fake-key'

        with patch('locations.utils.get_departure_coordinates.cache') as mock_cache, \
             patch('locations.utils.get_departure_coordinates.GoogleV3') as MockGeocoder:
            mock_cache.get.return_value = None
            MockGeocoder.return_value.geocode.side_effect = Exception('network error')

            result = get_departure_coordinates()

        assert result is None
