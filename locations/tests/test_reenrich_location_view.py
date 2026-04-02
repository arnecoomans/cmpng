import pytest
from unittest.mock import patch
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from django.contrib.auth.models import Permission

from locations.models.Location import Location
from locations.tests.factories import LocationFactory, RegionFactory, UserFactory
from locations.views.locations.reenrich_location import ReEnrichLocationView


def _make_staff_user():
  user = UserFactory(is_staff=True)
  user.user_permissions.add(Permission.objects.get(codename='delete_location'))
  return user


def _post(slug, user):
  request = RequestFactory().post(f'/location/{slug}/re-enrich/')
  request.user = user
  request.session = {}
  request._messages = FallbackStorage(request)
  return request


# ------------------------------------------------------------------ #
#  dispatch — permission check
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestReEnrichLocationViewPermissions:

  def test_non_staff_is_denied(self, db):
    user = UserFactory()
    location = LocationFactory()
    request = _post(location.slug, user)

    with pytest.raises(PermissionDenied):
      ReEnrichLocationView.as_view()(request, slug=location.slug)

  def test_non_staff_does_not_call_enrich(self, db):
    user = UserFactory()
    location = LocationFactory()
    request = _post(location.slug, user)

    with patch('locations.views.locations.reenrich_location.enrich_location') as mock_enrich:
      with pytest.raises(PermissionDenied):
        ReEnrichLocationView.as_view()(request, slug=location.slug)

    mock_enrich.assert_not_called()


# ------------------------------------------------------------------ #
#  post — staff clears fields and calls enrich_location
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestReEnrichLocationViewPost:

  def test_clears_address_before_enrich(self, db):
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    location = LocationFactory(address='france')
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location') as mock_enrich:
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    location.refresh_from_db()
    assert location.address is None

  def test_passes_address_hint_to_enrich(self, db):
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    location = LocationFactory(address='france')
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location') as mock_enrich:
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    _, kwargs = mock_enrich.call_args
    assert kwargs.get('address_hint') == 'france'

  def test_clears_google_place_id(self, db):
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    location = LocationFactory()
    Location.objects.filter(pk=location.pk).update(google_place_id='ChIJold')
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location'):
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    location.refresh_from_db()
    assert location.google_place_id is None

  def test_clears_geo(self, db):
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    country = RegionFactory(parent=None)
    region  = RegionFactory(parent=country)
    dept    = RegionFactory(parent=region)
    location = LocationFactory(geo=dept)
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location'):
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    location.refresh_from_db()
    assert location.geo is None

  def test_redirects_to_location_after_enrich(self, db):
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    location = LocationFactory()
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location'):
      response = ReEnrichLocationView.as_view()(request, slug=location.slug)

    assert response.status_code == 302
    assert location.slug in response['Location']

  def test_address_hint_is_none_when_no_address(self, db):
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    location = LocationFactory(address=None)
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location') as mock_enrich:
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    _, kwargs = mock_enrich.call_args
    assert kwargs.get('address_hint') is None

  def test_real_address_is_kept(self, db):
    """When address contains digits it is treated as a real address and kept."""
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    location = LocationFactory(address='49 rue de Cîteaux, 21700 Agencourt')
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location'):
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    location.refresh_from_db()
    assert location.address == '49 rue de Cîteaux, 21700 Agencourt'

  def test_real_address_clears_place_id_and_geo(self, db):
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    country = RegionFactory(parent=None)
    region  = RegionFactory(parent=country)
    dept    = RegionFactory(parent=region)
    location = LocationFactory(address='10 Main St, 1234 AB Town', geo=dept)
    Location.objects.filter(pk=location.pk).update(google_place_id='ChIJreal')
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location'):
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    location.refresh_from_db()
    assert location.google_place_id is None
    assert location.geo is None

  def test_real_address_clears_distance_to_departure_center(self, db):
    """The DB field is cleared before enrich runs (checked via DB update, not post-recalc)."""
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    location = LocationFactory(address='10 Main St, 1234 AB Town')
    Location.objects.filter(pk=location.pk).update(distance_to_departure_center=250)
    request = _post(location.slug, staff)

    cleared_values = {}

    def capture_enrich(loc, **kwargs):
      cleared_values['distance_to_departure_center'] = loc.distance_to_departure_center

    with patch('locations.views.locations.reenrich_location.enrich_location', side_effect=capture_enrich):
      with patch('locations.views.locations.reenrich_location.warn_nearby_duplicates'):
        with patch.object(location.__class__, 'calculate_distance_to_departure_center'):
          ReEnrichLocationView.as_view()(request, slug=location.slug)

    assert cleared_values['distance_to_departure_center'] is None

  def test_hint_address_clears_distance_to_departure_center(self, db):
    """The DB field is cleared before enrich runs for hint addresses."""
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    location = LocationFactory(address='france')
    Location.objects.filter(pk=location.pk).update(distance_to_departure_center=800)
    request = _post(location.slug, staff)

    cleared_values = {}

    def capture_enrich(loc, **kwargs):
      cleared_values['distance_to_departure_center'] = loc.distance_to_departure_center

    with patch('locations.views.locations.reenrich_location.enrich_location', side_effect=capture_enrich):
      with patch('locations.views.locations.reenrich_location.warn_nearby_duplicates'):
        with patch.object(location.__class__, 'calculate_distance_to_departure_center'):
          ReEnrichLocationView.as_view()(request, slug=location.slug)

    assert cleared_values['distance_to_departure_center'] is None

  def test_real_address_calls_enrich_without_hint(self, db):
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    location = LocationFactory(address='10 Main St, 1234 AB Town')
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location') as mock_enrich:
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    _, kwargs = mock_enrich.call_args
    assert 'address_hint' not in kwargs


# ------------------------------------------------------------------ #
#  warn_nearby_duplicates
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestReEnrichLocationViewNearbyWarning:

  def test_warn_nearby_duplicates_called_after_enrich(self, db):
    staff = _make_staff_user()
    staff.is_staff = True
    staff.save()
    location = LocationFactory()
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location'):
      with patch('locations.views.locations.reenrich_location.warn_nearby_duplicates') as mock_warn:
        ReEnrichLocationView.as_view()(request, slug=location.slug)

    mock_warn.assert_called_once()

  def test_warn_nearby_duplicates_not_called_for_non_staff(self, db):
    user = UserFactory()
    location = LocationFactory()
    request = _post(location.slug, user)

    with patch('locations.views.locations.reenrich_location.enrich_location'):
      with patch('locations.views.locations.reenrich_location.warn_nearby_duplicates') as mock_warn:
        with pytest.raises(PermissionDenied):
          ReEnrichLocationView.as_view()(request, slug=location.slug)

    mock_warn.assert_not_called()
