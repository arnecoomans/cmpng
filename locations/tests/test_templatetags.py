import pytest
from django.test import RequestFactory
from unittest.mock import MagicMock

from locations.templatetags.distance_tags import distance_between
from locations.templatetags.maps_tags import has_maps_consent, SESSION_KEY
from locations.tests.factories import (
    LocationFactory, DistanceFactory, UserFactory, UserPreferencesFactory,
)
from locations.models.List import Distance


# ------------------------------------------------------------------ #
#  distance_between
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestDistanceBetween:

  def test_returns_cached_distance(self):
    a = LocationFactory()
    b = LocationFactory()
    origin, destination = Distance.normalize(a, b)
    d = DistanceFactory(origin=origin, destination=destination)
    assert distance_between(a, b) == d

  def test_returns_none_on_cache_miss(self):
    a = LocationFactory()
    b = LocationFactory()
    assert distance_between(a, b) is None

  def test_returns_none_when_first_arg_is_none(self):
    b = LocationFactory()
    assert distance_between(None, b) is None

  def test_returns_none_when_second_arg_is_none(self):
    a = LocationFactory()
    assert distance_between(a, None) is None

  def test_returns_none_when_same_location(self):
    a = LocationFactory()
    assert distance_between(a, a) is None


# ------------------------------------------------------------------ #
#  has_maps_consent
# ------------------------------------------------------------------ #

def _make_context(request):
  return {'request': request}


def _request(user=None, params=None, session_data=None):
  rf = RequestFactory()
  req = rf.get('/', params or {})
  req.user = user or MagicMock(is_authenticated=False)
  req.session = session_data if session_data is not None else {}
  return req


@pytest.mark.django_db
class TestHasMapsConsent:

  def test_returns_false_without_request(self):
    assert has_maps_consent({}) is False

  def test_once_param_returns_true(self):
    req = _request(params={'external_maps_consent': 'once'})
    assert has_maps_consent(_make_context(req)) is True

  def test_once_param_does_not_save_to_session(self):
    session = {}
    req = _request(params={'external_maps_consent': 'once'}, session_data=session)
    has_maps_consent(_make_context(req))
    assert SESSION_KEY not in session

  def test_session_param_returns_true(self):
    req = _request(params={'external_maps_consent': 'session'})
    assert has_maps_consent(_make_context(req)) is True

  def test_session_param_saves_to_session(self):
    session = {}
    req = _request(params={'external_maps_consent': 'session'}, session_data=session)
    has_maps_consent(_make_context(req))
    assert session.get(SESSION_KEY) is True

  def test_always_param_saves_to_session_for_anonymous(self):
    session = {}
    req = _request(params={'external_maps_consent': 'always'}, session_data=session)
    assert has_maps_consent(_make_context(req)) is True
    assert session.get(SESSION_KEY) is True

  def test_always_param_saves_to_preferences_for_authenticated(self):
    user = UserFactory()
    prefs = UserPreferencesFactory(user=user, external_maps_consent=False)
    session = {}
    req = _request(user=user, params={'external_maps_consent': 'always'}, session_data=session)
    assert has_maps_consent(_make_context(req)) is True
    prefs.refresh_from_db()
    assert prefs.external_maps_consent is True

  def test_session_key_grants_consent(self):
    req = _request(session_data={SESSION_KEY: True})
    assert has_maps_consent(_make_context(req)) is True

  def test_user_preference_grants_consent(self):
    user = UserFactory()
    UserPreferencesFactory(user=user, external_maps_consent=True)
    req = _request(user=user)
    assert has_maps_consent(_make_context(req)) is True

  def test_user_preference_false_denies_consent(self):
    user = UserFactory()
    UserPreferencesFactory(user=user, external_maps_consent=False)
    req = _request(user=user)
    assert has_maps_consent(_make_context(req)) is False

  def test_no_consent_by_default(self):
    req = _request()
    assert has_maps_consent(_make_context(req)) is False

  def test_no_preferences_object_does_not_raise(self):
    """Authenticated user without preferences — exception swallowed, returns False."""
    user = UserFactory()
    req = _request(user=user)
    assert has_maps_consent(_make_context(req)) is False

  def test_always_param_no_preferences_object_does_not_raise(self):
    """always param for authenticated user without preferences — exception swallowed, returns True."""
    user = UserFactory()
    req = _request(user=user, params={'external_maps_consent': 'always'})
    assert has_maps_consent(_make_context(req)) is True
