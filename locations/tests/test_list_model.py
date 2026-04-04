import pytest
from unittest.mock import patch, PropertyMock
from django.db import IntegrityError
from django.test import RequestFactory

from locations.models import List, ListItem, Distance
from locations.tests.factories import (
    LocationFactory, UserFactory, ListFactory, ListItemFactory, DistanceFactory,
)


# ------------------------------------------------------------------ #
#  Distance
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestDistanceNormalize:

    def test_lower_pk_becomes_origin(self):
        a = LocationFactory()
        b = LocationFactory()
        low, high = (a, b) if a.pk < b.pk else (b, a)
        origin, destination = Distance.normalize(low, high)
        assert origin == low
        assert destination == high

    def test_normalize_swaps_when_needed(self):
        a = LocationFactory()
        b = LocationFactory()
        high, low = (a, b) if a.pk > b.pk else (b, a)
        origin, destination = Distance.normalize(high, low)
        assert origin == low
        assert destination == high

    def test_normalize_is_idempotent(self):
        a = LocationFactory()
        b = LocationFactory()
        first  = Distance.normalize(a, b)
        second = Distance.normalize(b, a)
        assert first == second


@pytest.mark.django_db
class TestDistanceHelpers:

    def test_distance_km(self):
        d = DistanceFactory(distance_m=150000.0)
        assert d.distance_km() == 150.0

    def test_duration_min(self):
        d = DistanceFactory(duration_s=5400.0)
        assert d.duration_min() == 90.0

    def test_duration_hr(self):
        d = DistanceFactory(duration_s=7200.0)
        assert d.duration_hr() == 2.0


@pytest.mark.django_db
class TestDistanceGetFor:

    def test_returns_cached_distance(self):
        a = LocationFactory()
        b = LocationFactory()
        origin, destination = Distance.normalize(a, b)
        d = DistanceFactory(origin=origin, destination=destination)
        assert Distance.get_for(a, b) == d

    def test_symmetric_lookup(self):
        """get_for(a, b) and get_for(b, a) return the same record."""
        a = LocationFactory()
        b = LocationFactory()
        origin, destination = Distance.normalize(a, b)
        d = DistanceFactory(origin=origin, destination=destination)
        assert Distance.get_for(a, b) == d
        assert Distance.get_for(b, a) == d

    def test_returns_none_on_miss(self):
        a = LocationFactory()
        b = LocationFactory()
        assert Distance.get_for(a, b) is None

    def test_unique_together_prevents_duplicates(self):
        a = LocationFactory()
        b = LocationFactory()
        origin, destination = Distance.normalize(a, b)
        DistanceFactory(origin=origin, destination=destination)
        with pytest.raises(IntegrityError):
            DistanceFactory(origin=origin, destination=destination)


# ------------------------------------------------------------------ #
#  List
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestListDefaults:

    def test_default_template_is_itinerary(self):
        trip = ListFactory()
        assert trip.template == List.TEMPLATE_ITINERARY

    def test_default_is_not_archived(self):
        trip = ListFactory()
        assert trip.is_archived is False

    def test_str(self):
        trip = ListFactory(name='Summer 2025')
        assert str(trip) == 'Summer 2025'

    def test_token_auto_generated(self):
        trip = ListFactory()
        assert trip.token
        assert len(trip.token) >= 10


@pytest.mark.django_db
class TestListSlug:

  def test_slug_auto_set_from_name(self):
    trip = ListFactory(name='Summer Road Trip')
    assert trip.slug == 'summer-road-trip'

  def test_slug_not_overwritten_on_resave(self):
    trip = ListFactory(name='My Trip')
    original_slug = trip.slug
    trip.name = 'Renamed Trip'
    trip.save()
    assert trip.slug == original_slug

  def test_explicit_slug_preserved(self):
    trip = ListFactory(name='My Trip', slug='custom-slug')
    assert trip.slug == 'custom-slug'

  def test_slug_unique(self):
    from django.db import IntegrityError
    ListFactory(name='Same Name', slug='same-name')
    with pytest.raises(IntegrityError):
      ListFactory(name='Same Name', slug='same-name')


@pytest.mark.django_db
class TestListIsRouted:

    def test_itinerary_is_routed(self):
        assert ListFactory(template=List.TEMPLATE_ITINERARY).is_routed is True

    def test_bucketlist_is_not_routed(self):
        assert ListFactory(template=List.TEMPLATE_BUCKETLIST).is_routed is False

    def test_themed_is_not_routed(self):
        assert ListFactory(template=List.TEMPLATE_THEMED).is_routed is False

    def test_logbook_is_not_routed(self):
        assert ListFactory(template=List.TEMPLATE_LOGBOOK).is_routed is False


@pytest.mark.django_db
class TestListOptimizedQueryset:

    def test_prefetches_items(self):
        trip = ListFactory()
        loc1 = LocationFactory()
        loc2 = LocationFactory()
        ListItemFactory(list=trip, location=loc1, order=0)
        ListItemFactory(list=trip, location=loc2, order=1)

        result = List.get_optimized_queryset().get(pk=trip.pk)

        # Access prefetch cache — should not fire additional queries
        items = list(result.items.all())
        assert len(items) == 2

    def test_items_ordered_by_order(self):
        trip = ListFactory()
        ListItemFactory(list=trip, order=2)
        ListItemFactory(list=trip, order=0)
        ListItemFactory(list=trip, order=1)

        result = List.get_optimized_queryset().get(pk=trip.pk)
        orders = [item.order for item in result.items.all()]
        assert orders == sorted(orders)


# ------------------------------------------------------------------ #
#  ListItem
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestListItemDefaults:

    def test_creates_with_required_fields(self):
        item = ListItemFactory()
        assert item.pk is not None
        assert item.note == ''
        assert item.stay_duration is None
        assert item.price_per_night is None
        assert item.media is None
        assert item.leg_distance is None

    def test_str(self):
        trip = ListFactory(name='My Trip')
        loc  = LocationFactory(name='Camping A')
        item = ListItemFactory(list=trip, location=loc, order=0)
        assert 'My Trip' in str(item)
        assert 'Camping A' in str(item)


@pytest.mark.django_db
class TestListItemConstraints:

    def test_unique_order_within_list(self):
        trip = ListFactory()
        ListItemFactory(list=trip, order=0)
        with pytest.raises(IntegrityError):
            ListItemFactory(list=trip, order=0)

    def test_same_order_allowed_in_different_lists(self):
        trip1 = ListFactory()
        trip2 = ListFactory()
        ListItemFactory(list=trip1, order=0)
        item2 = ListItemFactory(list=trip2, order=0)
        assert item2.pk is not None

    def test_deleting_list_cascades_to_items(self):
        trip = ListFactory()
        item = ListItemFactory(list=trip)
        pk   = item.pk
        trip.delete()
        assert not ListItem.objects.filter(pk=pk).exists()

    def test_deleting_location_cascades_to_items(self):
        loc  = LocationFactory()
        item = ListItemFactory(location=loc)
        pk   = item.pk
        loc.delete()
        assert not ListItem.objects.filter(pk=pk).exists()

    def test_deleting_distance_nulls_leg(self):
        trip = ListFactory()
        a    = LocationFactory()
        b    = LocationFactory()
        origin, destination = Distance.normalize(a, b)
        d    = DistanceFactory(origin=origin, destination=destination)
        item = ListItemFactory(list=trip, location=b, leg_distance=d)
        d.delete()
        item.refresh_from_db()
        assert item.leg_distance is None


# ------------------------------------------------------------------ #
#  Location.filtered_lists / has_lists
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationFilteredLists:

    def test_returns_lists_containing_location(self):
        location = LocationFactory()
        lst = ListFactory(status='p', visibility='p')
        ListItemFactory(list=lst, location=location)
        assert lst in location.filtered_lists()

    def test_excludes_unpublished_lists(self):
        location = LocationFactory()
        lst = ListFactory(status='c', visibility='p')
        ListItemFactory(list=lst, location=location)
        assert lst not in location.filtered_lists()

    def test_excludes_private_lists_without_request(self):
        location = LocationFactory()
        lst = ListFactory(status='p', visibility='q')
        ListItemFactory(list=lst, location=location)
        assert lst not in location.filtered_lists()

    def test_excludes_lists_not_containing_location(self):
        location = LocationFactory()
        other = LocationFactory()
        lst = ListFactory(status='p', visibility='p')
        ListItemFactory(list=lst, location=other)
        assert lst not in location.filtered_lists()

    def test_with_request_includes_community_lists(self):
        rf = RequestFactory()
        request = rf.get('/')
        request.user = UserFactory()
        location = LocationFactory()
        lst = ListFactory(status='p', visibility='c')
        ListItemFactory(list=lst, location=location)
        location.request = request
        assert lst in location.filtered_lists()


@pytest.mark.django_db
class TestLocationHasLists:

    def test_true_when_location_in_visible_list(self):
        location = LocationFactory()
        lst = ListFactory(status='p', visibility='p')
        ListItemFactory(list=lst, location=location)
        assert location.has_lists() is True

    def test_false_when_no_lists(self):
        location = LocationFactory()
        assert location.has_lists() is False

    def test_false_when_list_is_unpublished(self):
        location = LocationFactory()
        lst = ListFactory(status='c', visibility='p')
        ListItemFactory(list=lst, location=location)
        assert location.has_lists() is False


@pytest.mark.django_db
class TestLocationOwnedLists:

    def _request(self, user):
        rf = RequestFactory()
        request = rf.get('/')
        request.user = user
        return request

    def test_returns_own_lists(self):
        user = UserFactory()
        location = LocationFactory()
        lst = ListFactory(status='p', visibility='p', user=user)
        ListItemFactory(list=lst, location=location)
        location.request = self._request(user)
        assert lst in location.owned_lists()

    def test_excludes_other_users_lists(self):
        user = UserFactory()
        other = UserFactory()
        location = LocationFactory()
        lst = ListFactory(status='p', visibility='p', user=other)
        ListItemFactory(list=lst, location=location)
        location.request = self._request(user)
        assert lst not in location.owned_lists()

    def test_empty_without_request(self):
        location = LocationFactory()
        lst = ListFactory(status='p', visibility='p')
        ListItemFactory(list=lst, location=location)
        assert location.owned_lists().count() == 0


# ------------------------------------------------------------------ #
#  Distance.__str__
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestDistanceStr:

    def test_str_shows_distance_and_duration(self):
        d = DistanceFactory(distance_m=55000.0, duration_s=3600.0)
        s = str(d)
        assert '55.00 km' in s
        assert '60.00 min' in s


# ------------------------------------------------------------------ #
#  ListItem.__str__ fallback
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestListItemStrFallback:

    def test_str_fallback_when_location_missing(self):
        from unittest.mock import PropertyMock
        item = ListItemFactory()
        # Simulate broken FK by making .location raise
        with patch.object(type(item), 'location', new_callable=PropertyMock, side_effect=Exception):
            s = str(item)
        assert 'LOCATION' in s
