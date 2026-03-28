import pytest
from unittest.mock import patch
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from locations.models.Link import Link
from locations.models.Location import Location
from locations.tests.factories import CategoryFactory, LinkFactory, LocationFactory, UserFactory
from locations.views.locations.add_location import AddLocationView


def _post(data, user):
  request = RequestFactory().post('/location/add/', data)
  request.user = user
  request.session = {}
  request._messages = FallbackStorage(request)
  return request


def _get(user):
  request = RequestFactory().get('/location/add/')
  request.user = user
  request.session = {}
  request._messages = FallbackStorage(request)
  return request


# ------------------------------------------------------------------ #
#  form_valid
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestAddLocationViewFormValid:

  def test_creates_location_with_correct_user(self, db):
    user = UserFactory()
    request = _post({'name': 'Camping Test', 'visibility': 'p'}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates'):
        AddLocationView.as_view()(request)

    location = Location.objects.get(name='Camping Test')
    assert location.user == user

  def test_redirects_to_location_detail(self, db):
    user = UserFactory()
    request = _post({'name': 'Camping Test', 'visibility': 'p'}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates'):
        response = AddLocationView.as_view()(request)

    assert response.status_code == 302
    location = Location.objects.get(name='Camping Test')
    assert location.slug in response['Location']

  def test_calls_enrich_location(self, db):
    user = UserFactory()
    request = _post({'name': 'Camping Test', 'visibility': 'p'}, user)

    with patch('locations.views.locations.add_location.enrich_location') as mock_enrich:
      with patch('locations.views.locations.add_location.warn_nearby_duplicates'):
        AddLocationView.as_view()(request)

    mock_enrich.assert_called_once()
    args, kwargs = mock_enrich.call_args
    assert args[0].name == 'Camping Test'
    assert kwargs['request'] == request

  def test_adds_success_message(self, db):
    user = UserFactory()
    request = _post({'name': 'Camping Test', 'visibility': 'p'}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates'):
        AddLocationView.as_view()(request)

    msgs = list(get_messages(request))
    assert len(msgs) == 1
    assert 'successfully' in str(msgs[0]).lower()

  def test_sets_categories_when_submitted(self, db):
    user = UserFactory()
    cat = CategoryFactory(status='p')
    request = _post({'name': 'Camping Test', 'visibility': 'p', 'categories': cat.slug}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates'):
        AddLocationView.as_view()(request)

    location = Location.objects.get(name='Camping Test')
    assert cat in location.categories.all()

  def test_ignores_unknown_category_slugs(self, db):
    user = UserFactory()
    request = _post({'name': 'Camping Test', 'visibility': 'p', 'categories': 'does-not-exist'}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates'):
        AddLocationView.as_view()(request)

    location = Location.objects.get(name='Camping Test')
    assert location.categories.count() == 0

  def test_no_categories_when_not_submitted(self, db):
    user = UserFactory()
    request = _post({'name': 'Camping Test', 'visibility': 'p'}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates'):
        AddLocationView.as_view()(request)

    location = Location.objects.get(name='Camping Test')
    assert location.categories.count() == 0


# ------------------------------------------------------------------ #
#  form_invalid
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestAddLocationViewFormInvalid:

  def test_returns_200_on_invalid_form(self, db):
    user = UserFactory()
    request = _post({'name': ''}, user)  # name is required

    with patch('locations.views.locations.add_location.enrich_location'):
      response = AddLocationView.as_view()(request)

    assert response.status_code == 200

  def test_adds_error_message_on_invalid_form(self, db):
    user = UserFactory()
    request = _post({'name': ''}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      AddLocationView.as_view()(request)

    msgs = list(get_messages(request))
    assert len(msgs) == 1
    assert 'correct' in str(msgs[0]).lower()

  def test_does_not_call_enrich_on_invalid_form(self, db):
    user = UserFactory()
    request = _post({'name': ''}, user)

    with patch('locations.views.locations.add_location.enrich_location') as mock_enrich:
      AddLocationView.as_view()(request)

    mock_enrich.assert_not_called()


# ------------------------------------------------------------------ #
#  link_url
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestAddLocationViewLinkUrl:

  def test_creates_link_when_url_provided(self, db):
    user = UserFactory()
    request = _post({'name': 'Camping Test', 'visibility': 'p', 'link_url': 'https://example.com'}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates'):
        AddLocationView.as_view()(request)

    location = Location.objects.get(name='Camping Test')
    assert Link.objects.filter(url='https://example.com', location=location).exists()

  def test_no_link_when_url_not_provided(self, db):
    user = UserFactory()
    request = _post({'name': 'Camping Test', 'visibility': 'p'}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates'):
        AddLocationView.as_view()(request)

    location = Location.objects.get(name='Camping Test')
    assert Link.objects.filter(location=location).count() == 0

  def test_does_not_duplicate_existing_link(self, db):
    user = UserFactory()
    existing_location = LocationFactory()
    LinkFactory(url='https://example.com', location=existing_location)
    request = _post({'name': 'Camping Test', 'visibility': 'p', 'link_url': 'https://example.com'}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates'):
        AddLocationView.as_view()(request)

    assert Link.objects.filter(url='https://example.com').count() == 1


# ------------------------------------------------------------------ #
#  warn_nearby_duplicates
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestAddLocationViewNearbyWarning:

  def test_warn_nearby_duplicates_called_after_enrich(self, db):
    user = UserFactory()
    request = _post({'name': 'Camping Test', 'visibility': 'p'}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates') as mock_warn:
        AddLocationView.as_view()(request)

    mock_warn.assert_called_once()

  def test_warn_nearby_duplicates_not_called_on_invalid_form(self, db):
    user = UserFactory()
    request = _post({'name': ''}, user)

    with patch('locations.views.locations.add_location.enrich_location'):
      with patch('locations.views.locations.add_location.warn_nearby_duplicates') as mock_warn:
        AddLocationView.as_view()(request)

    mock_warn.assert_not_called()
