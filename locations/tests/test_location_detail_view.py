import pytest
from django.urls import reverse
from django.conf import settings
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore

from locations.tests.factories import LocationFactory, UserFactory
from locations.views.locations.location_detail import LocationDetailView


def make_request(user, url='/'):
  """Build a GET request with the given user, with session and messages middleware."""
  factory = RequestFactory()
  request = factory.get(url)
  request.user = user
  request.session = SessionStore()
  request._messages = FallbackStorage(request)
  return request


def detail_url(location):
  return reverse('locations:location_detail', kwargs={'slug': location.slug})


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def public_location(db):
  return LocationFactory(status='p', visibility='p')

@pytest.fixture
def community_location(db):
  return LocationFactory(status='p', visibility='c')

@pytest.fixture
def private_location(db):
  return LocationFactory(status='p', visibility='q')



# ------------------------------------------------------------------ #
#  Basic access — public location
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationDetailViewBasics:

  def test_public_location_returns_200_for_anonymous(self, client, public_location):
    response = client.get(detail_url(public_location))
    assert response.status_code == 200

  def test_public_location_uses_correct_template(self, client, public_location):
    response = client.get(detail_url(public_location))
    assert 'locations/location_detail.html' in [t.name for t in response.templates]

  def test_location_in_context(self, client, public_location):
    response = client.get(detail_url(public_location))
    assert response.context['location'] == public_location

  def test_nonexistent_slug_returns_404(self, client):
    url = reverse('locations:location_detail', kwargs={'slug': 'does-not-exist'})
    response = client.get(url)
    assert response.status_code == 404

  def test_scope_is_location(self, client, public_location):
    response = client.get(detail_url(public_location))
    assert response.context['scope'] == 'location'


# ------------------------------------------------------------------ #
#  Visibility — anonymous users
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationDetailViewAnonymousAccess:

  def test_community_location_redirects_anonymous_to_login(self, client, community_location):
    response = client.get(detail_url(community_location))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response['Location']

  def test_private_location_redirects_anonymous_to_login(self, client, private_location):
    response = client.get(detail_url(private_location))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response['Location']

  def test_redirect_includes_next_param(self, client, community_location):
    url = detail_url(community_location)
    response = client.get(url)
    assert f'next={url}' in response['Location']


# ------------------------------------------------------------------ #
#  Visibility — authenticated users
#  Uses RequestFactory to bypass session/cookie issues with pytest-django
#  and test view logic directly with a real authenticated user object.
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationDetailViewAuthenticatedAccess:

  def test_community_location_returns_200_for_authenticated(self, db):
    user = UserFactory()
    location = LocationFactory(status='p', visibility='c')
    request = make_request(user, detail_url(location))
    response = LocationDetailView.as_view()(request, slug=location.slug)
    assert response.status_code == 200

  def test_public_location_returns_200_for_authenticated(self, db):
    user = UserFactory()
    location = LocationFactory(status='p', visibility='p')
    request = make_request(user, detail_url(location))
    response = LocationDetailView.as_view()(request, slug=location.slug)
    assert response.status_code == 200

  def test_private_location_of_another_user_returns_403(self, db):
    user = UserFactory()
    other_user = UserFactory()
    location = LocationFactory(status='p', visibility='q', user=other_user)
    request = make_request(user, detail_url(location))
    response = LocationDetailView.as_view()(request, slug=location.slug)
    assert response.status_code == 403

  def test_private_location_returns_200_for_owner(self, db):
    user = UserFactory()
    location = LocationFactory(status='p', visibility='q', user=user)
    request = make_request(user, detail_url(location))
    response = LocationDetailView.as_view()(request, slug=location.slug)
    assert response.status_code == 200

  def test_403_uses_private_error_template(self, db):
    user = UserFactory()
    other_user = UserFactory()
    location = LocationFactory(status='p', visibility='q', user=other_user)
    request = make_request(user, detail_url(location))
    response = LocationDetailView.as_view()(request, slug=location.slug)
    assert response.status_code == 403


# ------------------------------------------------------------------ #
#  Context data
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationDetailViewContext:

  def test_description_shown_to_authenticated_user(self, client, public_location):
    user = UserFactory()
    user.save()
    public_location.description = 'A community description'
    public_location.save()
    client.force_login(user)
    response = client.get(detail_url(public_location))
    assert b'A community description' in response.content

  def test_description_hidden_from_anonymous(self, client, public_location):
    public_location.description = 'Hidden from anon'
    public_location.save()
    response = client.get(detail_url(public_location))
    assert b'Hidden from anon' not in response.content

  def test_filtered_media_in_context(self, client, public_location):
    response = client.get(detail_url(public_location))
    assert 'filtered_media' in response.context
