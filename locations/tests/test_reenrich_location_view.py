import pytest
from unittest.mock import patch
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from locations.models.Location import Location
from locations.tests.factories import LocationFactory, RegionFactory, UserFactory
from locations.views.locations.reenrich_location import ReEnrichLocationView


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

  def test_non_staff_gets_warning_message(self, db):
    user = UserFactory()
    location = LocationFactory()
    request = _post(location.slug, user)

    ReEnrichLocationView.as_view()(request, slug=location.slug)

    msgs = list(get_messages(request))
    assert len(msgs) == 1
    assert 'not allowed' in str(msgs[0]).lower()

  def test_non_staff_is_redirected_to_location(self, db):
    user = UserFactory()
    location = LocationFactory()
    request = _post(location.slug, user)

    response = ReEnrichLocationView.as_view()(request, slug=location.slug)

    assert response.status_code == 302
    assert location.slug in response['Location']

  def test_non_staff_does_not_call_enrich(self, db):
    user = UserFactory()
    location = LocationFactory()
    request = _post(location.slug, user)

    with patch('locations.views.locations.reenrich_location.enrich_location') as mock_enrich:
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    mock_enrich.assert_not_called()


# ------------------------------------------------------------------ #
#  post — staff clears fields and calls enrich_location
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestReEnrichLocationViewPost:

  def test_clears_address_before_enrich(self, db):
    staff = UserFactory()
    staff.is_staff = True
    staff.save()
    location = LocationFactory(address='france')
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location') as mock_enrich:
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    location.refresh_from_db()
    assert location.address is None

  def test_passes_address_hint_to_enrich(self, db):
    staff = UserFactory()
    staff.is_staff = True
    staff.save()
    location = LocationFactory(address='france')
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location') as mock_enrich:
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    _, kwargs = mock_enrich.call_args
    assert kwargs.get('address_hint') == 'france'

  def test_clears_google_place_id(self, db):
    staff = UserFactory()
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
    staff = UserFactory()
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
    staff = UserFactory()
    staff.is_staff = True
    staff.save()
    location = LocationFactory()
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location'):
      response = ReEnrichLocationView.as_view()(request, slug=location.slug)

    assert response.status_code == 302
    assert location.slug in response['Location']

  def test_address_hint_is_none_when_no_address(self, db):
    staff = UserFactory()
    staff.is_staff = True
    staff.save()
    location = LocationFactory(address=None)
    request = _post(location.slug, staff)

    with patch('locations.views.locations.reenrich_location.enrich_location') as mock_enrich:
      ReEnrichLocationView.as_view()(request, slug=location.slug)

    _, kwargs = mock_enrich.call_args
    assert kwargs.get('address_hint') is None


# ------------------------------------------------------------------ #
#  warn_nearby_duplicates
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestReEnrichLocationViewNearbyWarning:

  def test_warn_nearby_duplicates_called_after_enrich(self, db):
    staff = UserFactory()
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
        ReEnrichLocationView.as_view()(request, slug=location.slug)

    mock_warn.assert_not_called()
