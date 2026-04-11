import pytest
from unittest.mock import patch, MagicMock

from locations.models.Preferences import App, UserPreferences
from locations.tests.factories import UserFactory, LocationFactory, UserPreferencesFactory


# ------------------------------------------------------------------ #
#  App model
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestAppModel:

  def test_str_returns_label(self, db):
    app = App.objects.create(
      slug='waze',
      label='Waze',
      url_format='https://waze.com/ul?ll={lat},{lon}',
    )
    assert str(app) == 'Waze'

  def test_ordering_by_label(self, db):
    App.objects.create(slug='z-app', label='Zebra', url_format='https://z.com')
    App.objects.create(slug='a-app', label='Alpha', url_format='https://a.com')
    labels = list(App.objects.values_list('label', flat=True))
    assert labels == sorted(labels)


# ------------------------------------------------------------------ #
#  UserPreferences model
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestUserPreferencesModel:

  def test_str_returns_username(self, db):
    user = UserFactory()
    user.save()
    prefs = UserPreferencesFactory(user=user)
    assert str(prefs) == f'Preferences for {user.username}'

  def test_all_apps_returns_list(self, db):
    user = UserFactory()
    user.save()
    prefs = UserPreferencesFactory(user=user)
    app = App.objects.create(
      slug='google-maps',
      label='Google Maps',
      url_format='https://maps.google.com/?q={lat},{lon}',
    )
    result = prefs.all_apps()
    assert isinstance(result, list)
    assert any(a['slug'] == 'google-maps' for a in result)

  def test_all_apps_includes_enabled_flag(self, db):
    user = UserFactory()
    user.save()
    prefs = UserPreferencesFactory(user=user)
    app = App.objects.create(
      slug='waze',
      label='Waze',
      url_format='https://waze.com/ul?ll={lat},{lon}',
    )
    prefs.apps.add(app)
    result = prefs.all_apps()
    entry = next(a for a in result if a['slug'] == 'waze')
    assert entry['enabled'] is True

  def test_all_apps_disabled_when_not_added(self, db):
    user = UserFactory()
    user.save()
    prefs = UserPreferencesFactory(user=user)
    App.objects.create(
      slug='apple-maps',
      label='Apple Maps',
      url_format='https://maps.apple.com/?ll={lat},{lon}',
    )
    result = prefs.all_apps()
    entry = next(a for a in result if a['slug'] == 'apple-maps')
    assert entry['enabled'] is False

  def _prefs_with_request(self, user):
    from unittest.mock import MagicMock
    prefs = UserPreferencesFactory(user=user)
    request = MagicMock()
    request.user = MagicMock()
    request.user.is_authenticated = True
    prefs.request = request
    return prefs

  def test_available_family_excludes_self(self, db):
    user = UserFactory()
    user.save()
    prefs = self._prefs_with_request(user)
    result = list(prefs.available_family())
    ids = [u['id'] for u in result]
    assert user.pk not in ids

  def test_available_family_excludes_existing_family(self, db):
    user = UserFactory()
    user.save()
    family_member = UserFactory()
    family_member.save()
    prefs = self._prefs_with_request(user)
    prefs.family.add(family_member)
    result = list(prefs.available_family())
    ids = [u['id'] for u in result]
    assert family_member.pk not in ids

  def test_available_family_includes_other_users(self, db):
    user = UserFactory()
    user.save()
    other = UserFactory()
    other.save()
    prefs = self._prefs_with_request(user)
    result = list(prefs.available_family())
    ids = [u['id'] for u in result]
    assert other.pk in ids


