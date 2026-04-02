import pytest
from django.conf import settings
from django.urls import reverse

from locations.models.Preferences import UserPreferences
from locations.tests.factories import UserFactory, UserPreferencesFactory
from locations.templatetags.maps_tags import SESSION_KEY


def force_login(client, user):
  user.save()
  client.force_login(user)


# ------------------------------------------------------------------ #
#  PreferencesView
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestPreferencesView:

  def test_redirects_anonymous_to_login(self, client):
    response = client.get(reverse('locations:preferences'))
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  def test_accessible_to_authenticated(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.get(reverse('locations:preferences'))
    assert response.status_code == 200

  def test_context_contains_preferences(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.get(reverse('locations:preferences'))
    assert 'preferences' in response.context

  def test_creates_preferences_if_missing(self, client):
    user = UserFactory()
    force_login(client, user)
    from locations.models.Preferences import UserPreferences
    assert not UserPreferences.objects.filter(user=user).exists()
    client.get(reverse('locations:preferences'))
    assert UserPreferences.objects.filter(user=user).exists()

  def test_reuses_existing_preferences(self, client):
    user = UserFactory()
    prefs = UserPreferencesFactory(user=user)
    force_login(client, user)
    response = client.get(reverse('locations:preferences'))
    assert response.context['preferences'].pk == prefs.pk

  def test_context_contains_available_apps(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.get(reverse('locations:preferences'))
    assert 'available_apps' in response.context


# ------------------------------------------------------------------ #
#  RevokeMapsSessionView
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestRevokeMapsSessionView:

  def test_redirects_anonymous_to_login(self, client):
    response = client.post(reverse('locations:revoke_maps_session'))
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  def test_clears_maps_consent_session_key(self, client):
    user = UserFactory()
    force_login(client, user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    client.post(reverse('locations:revoke_maps_session'))
    assert SESSION_KEY not in client.session

  def test_redirects_to_preferences(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:revoke_maps_session'))
    assert response.status_code == 302
    assert response['Location'] == reverse('locations:preferences')

  def test_safe_when_session_key_not_set(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:revoke_maps_session'))
    assert response.status_code == 302


# ------------------------------------------------------------------ #
#  SetLanguageView
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestSetLanguageView:

  def test_redirects_anonymous_to_login(self, client):
    response = client.post(reverse('locations:set_language'), {'language': 'en'})
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  def test_valid_language_saves_preference(self, client):
    user = UserFactory()
    force_login(client, user)
    client.post(reverse('locations:set_language'), {'language': 'nl'})
    prefs = UserPreferences.objects.get(user=user)
    assert prefs.language == 'nl'

  def test_valid_language_redirects_to_preferences(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:set_language'), {'language': 'en'})
    assert response.status_code == 302
    assert response['Location'] == reverse('locations:preferences')

  def test_valid_language_sets_cookie(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:set_language'), {'language': 'nl'})
    assert settings.LANGUAGE_COOKIE_NAME in response.cookies

  def test_invalid_language_redirects_without_saving(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:set_language'), {'language': 'xx'})
    assert response.status_code == 302
    assert not UserPreferences.objects.filter(user=user).exists()

  def test_creates_preferences_if_missing(self, client):
    user = UserFactory()
    force_login(client, user)
    assert not UserPreferences.objects.filter(user=user).exists()
    client.post(reverse('locations:set_language'), {'language': 'en'})
    assert UserPreferences.objects.filter(user=user).exists()
