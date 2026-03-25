import pytest
from unittest.mock import patch, MagicMock

from locations.models import Distance, ListItem
from locations.services.list_distance import (
    get_or_fetch_distance,
    resolve_leg,
    resolve_all_legs,
    on_item_saved,
    on_item_deleted,
    _fetch_from_google,
)
from locations.tests.factories import (
    LocationFactory, UserFactory, UserPreferencesFactory,
    ListFactory, ListItemFactory, DistanceFactory,
)


def _mock_distance_matrix(distance_m=100000, duration_s=3600, status='OK'):
  client = MagicMock()
  client.distance_matrix.return_value = {
    'rows': [{'elements': [{'status': status, 'distance': {'value': distance_m}, 'duration': {'value': duration_s}}]}]
  }
  return client


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def _make_list_with_home(user=None):
    """Return a list owned by a user with a home location set."""
    user = user or UserFactory()
    home = LocationFactory(name='Home')
    prefs = UserPreferencesFactory(user=user, home=home)
    trip = ListFactory(user=user)
    return trip, home


# ------------------------------------------------------------------ #
#  get_or_fetch_distance
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetOrFetchDistance:

    def test_returns_cached_without_api_call(self):
        a = LocationFactory()
        b = LocationFactory()
        origin, destination = Distance.normalize(a, b)
        cached = DistanceFactory(origin=origin, destination=destination, distance_m=50000.0)

        with patch('locations.services.list_distance._fetch_from_google') as mock_fetch:
            result = get_or_fetch_distance(a, b)

        mock_fetch.assert_not_called()
        assert result == cached

    def test_calls_api_on_cache_miss(self):
        a = LocationFactory(coord_lat='52.0', coord_lon='5.0')
        b = LocationFactory(coord_lat='48.0', coord_lon='2.0')

        with patch('locations.services.list_distance._fetch_from_google', return_value=(800000.0, 25200.0)) as mock_fetch:
            result = get_or_fetch_distance(a, b)

        mock_fetch.assert_called_once()
        assert result is not None
        assert result.distance_m == 800000.0
        assert result.duration_s == 25200.0

    def test_stores_normalized(self):
        a = LocationFactory(coord_lat='52.0', coord_lon='5.0')
        b = LocationFactory(coord_lat='48.0', coord_lon='2.0')
        low, high = Distance.normalize(a, b)

        with patch('locations.services.list_distance._fetch_from_google', return_value=(100000.0, 3600.0)):
            get_or_fetch_distance(a, b)

        d = Distance.objects.get(origin=low, destination=high)
        assert d.distance_m == 100000.0

    def test_returns_none_on_api_error(self):
        a = LocationFactory()
        b = LocationFactory()

        with patch('locations.services.list_distance._fetch_from_google', side_effect=ValueError('no coords')):
            result = get_or_fetch_distance(a, b)

        assert result is None


# ------------------------------------------------------------------ #
#  resolve_leg — previous location resolution
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestResolveLegPreviousLocation:

    def test_first_item_uses_home(self):
        trip, home = _make_list_with_home()
        loc  = LocationFactory(coord_lat='48.0', coord_lon='2.0')
        item = ListItemFactory(list=trip, location=loc, order=0)

        with patch('locations.services.list_distance._fetch_from_google', return_value=(500.0, 300.0)):
            distance = resolve_leg(item)

        assert distance is not None
        origin, destination = Distance.normalize(home, loc)
        assert distance.origin == origin
        assert distance.destination == destination

    def test_subsequent_item_uses_previous_location(self):
        trip, home = _make_list_with_home()
        loc1 = LocationFactory(coord_lat='46.0', coord_lon='3.0')
        loc2 = LocationFactory(coord_lat='44.0', coord_lon='1.0')
        ListItemFactory(list=trip, location=loc1, order=0)
        item2 = ListItemFactory(list=trip, location=loc2, order=1)

        with patch('locations.services.list_distance._fetch_from_google', return_value=(200.0, 120.0)):
            distance = resolve_leg(item2)

        assert distance is not None
        origin, destination = Distance.normalize(loc1, loc2)
        assert distance.origin == origin
        assert distance.destination == destination

    def test_no_home_returns_none(self):
        user = UserFactory()
        UserPreferencesFactory(user=user, home=None)
        trip = ListFactory(user=user)
        item = ListItemFactory(list=trip, order=0)

        result = resolve_leg(item)
        assert result is None


@pytest.mark.django_db
class TestResolveLegCacheBehaviour:

    def test_fetch_false_returns_none_on_miss(self):
        trip, home = _make_list_with_home()
        item = ListItemFactory(list=trip, order=0)

        with patch('locations.services.list_distance._fetch_from_google') as mock_fetch:
            result = resolve_leg(item, fetch=False)

        mock_fetch.assert_not_called()
        assert result is None

    def test_fetch_false_returns_cached(self):
        trip, home = _make_list_with_home()
        loc  = LocationFactory()
        item = ListItemFactory(list=trip, location=loc, order=0)
        origin, destination = Distance.normalize(home, loc)
        cached = DistanceFactory(origin=origin, destination=destination)

        result = resolve_leg(item, fetch=False)
        assert result == cached

    def test_saves_leg_distance_on_item(self):
        trip, home = _make_list_with_home()
        loc  = LocationFactory(coord_lat='48.0', coord_lon='2.0')
        item = ListItemFactory(list=trip, location=loc, order=0)

        with patch('locations.services.list_distance._fetch_from_google', return_value=(100.0, 60.0)):
            resolve_leg(item)

        item.refresh_from_db()
        assert item.leg_distance is not None

    def test_does_not_save_if_unchanged(self):
        """resolve_leg skips the save if leg_distance is already correct."""
        trip, home = _make_list_with_home()
        loc  = LocationFactory()
        item = ListItemFactory(list=trip, location=loc, order=0)
        origin, destination = Distance.normalize(home, loc)
        d = DistanceFactory(origin=origin, destination=destination)
        item.leg_distance = d
        item.save()

        with patch.object(ListItem, 'save') as mock_save:
            resolve_leg(item, fetch=False)

        mock_save.assert_not_called()


# ------------------------------------------------------------------ #
#  resolve_all_legs
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestResolveAllLegs:

    def test_resolves_all_items(self):
        trip, home = _make_list_with_home()
        locs = [LocationFactory(coord_lat=str(45 + i), coord_lon='2.0') for i in range(3)]
        for i, loc in enumerate(locs):
            ListItemFactory(list=trip, location=loc, order=i)

        with patch('locations.services.list_distance._fetch_from_google', return_value=(100.0, 60.0)):
            stats = resolve_all_legs(trip)

        assert stats['resolved'] == 3
        assert stats['failed'] == 0

    def test_counts_failed_when_no_home(self):
        user = UserFactory()
        UserPreferencesFactory(user=user, home=None)
        trip = ListFactory(user=user)
        ListItemFactory(list=trip, order=0)

        stats = resolve_all_legs(trip, fetch=False)
        assert stats['failed'] == 1


# ------------------------------------------------------------------ #
#  on_item_saved / on_item_deleted
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestOnItemSaved:

    def test_resolves_current_item(self):
        trip, home = _make_list_with_home()
        loc  = LocationFactory(coord_lat='48.0', coord_lon='2.0')
        item = ListItemFactory(list=trip, location=loc, order=0)

        with patch('locations.services.list_distance._fetch_from_google', return_value=(100.0, 60.0)):
            on_item_saved(item)

        item.refresh_from_db()
        assert item.leg_distance is not None

    def test_also_resolves_next_item(self):
        trip, home = _make_list_with_home()
        loc1 = LocationFactory(coord_lat='48.0', coord_lon='2.0')
        loc2 = LocationFactory(coord_lat='46.0', coord_lon='3.0')
        item1 = ListItemFactory(list=trip, location=loc1, order=0)
        item2 = ListItemFactory(list=trip, location=loc2, order=1)

        with patch('locations.services.list_distance._fetch_from_google', return_value=(100.0, 60.0)):
            on_item_saved(item1)

        item2.refresh_from_db()
        assert item2.leg_distance is not None

    def test_no_next_item_does_not_raise(self):
        trip, home = _make_list_with_home()
        loc  = LocationFactory(coord_lat='48.0', coord_lon='2.0')
        item = ListItemFactory(list=trip, location=loc, order=0)

        with patch('locations.services.list_distance._fetch_from_google', return_value=(100.0, 60.0)):
            on_item_saved(item)  # should not raise


@pytest.mark.django_db
class TestOnItemDeleted:

    def test_resolves_next_item_after_deletion(self):
        trip, home = _make_list_with_home()
        loc1 = LocationFactory(coord_lat='48.0', coord_lon='2.0')
        loc2 = LocationFactory(coord_lat='46.0', coord_lon='3.0')
        item1 = ListItemFactory(list=trip, location=loc1, order=0)
        item2 = ListItemFactory(list=trip, location=loc2, order=1)
        deleted_order = item1.order
        item1.delete()

        with patch('locations.services.list_distance._fetch_from_google', return_value=(500.0, 300.0)):
            on_item_deleted(trip, deleted_order)

        item2.refresh_from_db()
        assert item2.leg_distance is not None

    def test_no_next_item_does_not_raise(self):
        trip, home = _make_list_with_home()
        item = ListItemFactory(list=trip, order=0)
        deleted_order = item.order
        item.delete()

        on_item_deleted(trip, deleted_order)  # should not raise


# ------------------------------------------------------------------ #
#  _fetch_from_google
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestFetchFromGoogle:

    def test_raises_when_origin_has_no_coordinates(self, db):
        origin = LocationFactory(coord_lat=None, coord_lon=None)
        destination = LocationFactory(coord_lat='48.0', coord_lon='2.0')

        with pytest.raises(ValueError, match="Origin"):
            _fetch_from_google(origin, destination)

    def test_raises_when_destination_has_no_coordinates(self, db):
        origin = LocationFactory(coord_lat='52.0', coord_lon='5.0')
        destination = LocationFactory(coord_lat=None, coord_lon=None)

        with pytest.raises(ValueError, match="Destination"):
            _fetch_from_google(origin, destination)

    @patch('locations.services.list_distance.googlemaps.Client')
    def test_returns_distance_and_duration_on_success(self, mock_client_cls, db):
        mock_client_cls.return_value = _mock_distance_matrix(distance_m=800000, duration_s=25200)
        origin      = LocationFactory(coord_lat='52.0', coord_lon='5.0')
        destination = LocationFactory(coord_lat='48.0', coord_lon='2.0')

        distance_m, duration_s = _fetch_from_google(origin, destination)

        assert distance_m == 800000.0
        assert duration_s == 25200.0

    @patch('locations.services.list_distance.googlemaps.Client')
    def test_raises_when_api_status_not_ok(self, mock_client_cls, db):
        mock_client_cls.return_value = _mock_distance_matrix(status='NOT_FOUND')
        origin      = LocationFactory(coord_lat='52.0', coord_lon='5.0')
        destination = LocationFactory(coord_lat='48.0', coord_lon='2.0')

        with pytest.raises(ValueError, match="NOT_FOUND"):
            _fetch_from_google(origin, destination)

    @patch('locations.services.list_distance.googlemaps.Client')
    def test_raises_on_malformed_response(self, mock_client_cls, db):
        client = MagicMock()
        client.distance_matrix.return_value = {'rows': []}  # no elements key
        mock_client_cls.return_value = client
        origin      = LocationFactory(coord_lat='52.0', coord_lon='5.0')
        destination = LocationFactory(coord_lat='48.0', coord_lon='2.0')

        with pytest.raises(ValueError, match="Unexpected"):
            _fetch_from_google(origin, destination)


# ------------------------------------------------------------------ #
#  get_or_fetch_distance — error branch with request
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetOrFetchDistanceWithRequest:

    def test_adds_error_message_when_api_fails_and_request_provided(self, db):
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.messages import get_messages

        a = LocationFactory()
        b = LocationFactory()
        request = RequestFactory().get('/')
        request.session = {}
        request._messages = FallbackStorage(request)

        with patch('locations.services.list_distance._fetch_from_google', side_effect=ValueError('no coords')):
            result = get_or_fetch_distance(a, b, request=request)

        assert result is None
        msgs = list(get_messages(request))
        assert len(msgs) == 1
        assert 'no coords' in str(msgs[0])
