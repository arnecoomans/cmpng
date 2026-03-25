"""
Tests for VisibilityModel.filter_visibility() and VisibilityModel.is_visible_to().

Uses Location as the concrete VisibilityModel subclass.
Family visibility tests require UserPreferences with a family M2M relation.
"""
import pytest
from unittest.mock import Mock
from django.contrib.auth.models import AnonymousUser

from locations.models import Location
from locations.tests.factories import LocationFactory, UserFactory, UserPreferencesFactory


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def anon_request():
  req = Mock()
  req.user = AnonymousUser()
  return req


def auth_request(user):
  # Use the real User instance directly — is_authenticated is a
  # read-only property on Django's User and cannot be set.
  req = Mock()
  req.user = user
  return req


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def owner(db):
  return UserFactory()


@pytest.fixture
def other(db):
  return UserFactory()


@pytest.fixture
def family_member(db):
  return UserFactory()


@pytest.fixture
def owner_with_family(owner, family_member):
  prefs = UserPreferencesFactory(user=owner)
  prefs.family.add(family_member)
  return owner


@pytest.fixture
def public_loc(owner):
  return LocationFactory(visibility='p', user=owner)


@pytest.fixture
def community_loc(owner):
  return LocationFactory(visibility='c', user=owner)


@pytest.fixture
def family_loc(owner_with_family):
  return LocationFactory(visibility='f', user=owner_with_family)


@pytest.fixture
def private_loc(owner):
  return LocationFactory(visibility='q', user=owner)


# ------------------------------------------------------------------ #
#  filter_visibility — queryset-level filtering
# ------------------------------------------------------------------ #

class TestFilterVisibilityAnonymous:

  def test_public_visible_to_anon(self, db, public_loc):
    qs = Location.filter_visibility(Location.objects.all(), request=anon_request())
    assert public_loc in qs

  def test_community_hidden_from_anon(self, db, community_loc):
    qs = Location.filter_visibility(Location.objects.all(), request=anon_request())
    assert community_loc not in qs

  def test_family_hidden_from_anon(self, db, family_loc):
    qs = Location.filter_visibility(Location.objects.all(), request=anon_request())
    assert family_loc not in qs

  def test_private_hidden_from_anon(self, db, private_loc):
    qs = Location.filter_visibility(Location.objects.all(), request=anon_request())
    assert private_loc not in qs

  def test_no_request_shows_only_public(self, db, public_loc, community_loc):
    qs = Location.filter_visibility(Location.objects.all(), request=None)
    assert public_loc in qs
    assert community_loc not in qs


class TestFilterVisibilityAuthenticated:

  def test_public_visible_to_authenticated(self, db, public_loc, other):
    qs = Location.filter_visibility(Location.objects.all(), request=auth_request(other))
    assert public_loc in qs

  def test_community_visible_to_authenticated(self, db, community_loc, other):
    qs = Location.filter_visibility(Location.objects.all(), request=auth_request(other))
    assert community_loc in qs

  def test_family_visible_to_owner(self, db, family_loc, owner_with_family):
    qs = Location.filter_visibility(Location.objects.all(), request=auth_request(owner_with_family))
    assert family_loc in qs

  def test_family_visible_to_family_member(self, db, family_loc, family_member):
    qs = Location.filter_visibility(Location.objects.all(), request=auth_request(family_member))
    assert family_loc in qs

  def test_family_hidden_from_unrelated_user(self, db, family_loc, other):
    qs = Location.filter_visibility(Location.objects.all(), request=auth_request(other))
    assert family_loc not in qs

  def test_private_visible_to_owner(self, db, private_loc, owner):
    qs = Location.filter_visibility(Location.objects.all(), request=auth_request(owner))
    assert private_loc in qs

  def test_private_hidden_from_other_user(self, db, private_loc, other):
    qs = Location.filter_visibility(Location.objects.all(), request=auth_request(other))
    assert private_loc not in qs

  def test_mixed_queryset_filters_correctly(self, db, public_loc, community_loc, private_loc, other):
    qs = Location.filter_visibility(Location.objects.all(), request=auth_request(other))
    assert public_loc in qs
    assert community_loc in qs
    assert private_loc not in qs


# ------------------------------------------------------------------ #
#  is_visible_to — instance-level checks
# ------------------------------------------------------------------ #

class TestIsVisibleToPublic:

  def test_public_visible_to_none(self, db, public_loc):
    assert public_loc.is_visible_to(None) is True

  def test_public_visible_to_anon_user(self, db, public_loc):
    anon = Mock(is_authenticated=False)
    assert public_loc.is_visible_to(anon) is True

  def test_public_visible_to_any_user(self, db, public_loc, other):
    assert public_loc.is_visible_to(other) is True


class TestIsVisibleToCommunity:

  def test_community_hidden_from_none(self, db, community_loc):
    assert community_loc.is_visible_to(None) is False

  def test_community_hidden_from_anon(self, db, community_loc):
    anon = Mock(is_authenticated=False)
    assert community_loc.is_visible_to(anon) is False

  def test_community_visible_to_authenticated(self, db, community_loc, other):
    assert community_loc.is_visible_to(other) is True


class TestIsVisibleToFamily:

  def test_family_visible_to_owner(self, db, family_loc, owner_with_family):
    assert family_loc.is_visible_to(owner_with_family) is True

  def test_family_visible_to_family_member(self, db, family_loc, family_member):
    assert family_loc.is_visible_to(family_member) is True

  def test_family_hidden_from_unrelated_user(self, db, family_loc, other):
    assert family_loc.is_visible_to(other) is False

  def test_family_hidden_from_none(self, db, family_loc):
    assert family_loc.is_visible_to(None) is False


class TestIsVisibleToPrivate:

  def test_private_visible_to_owner(self, db, private_loc, owner):
    assert private_loc.is_visible_to(owner) is True

  def test_private_hidden_from_other_user(self, db, private_loc, other):
    assert private_loc.is_visible_to(other) is False

  def test_private_hidden_from_none(self, db, private_loc):
    assert private_loc.is_visible_to(None) is False

  def test_private_hidden_from_anon(self, db, private_loc):
    anon = Mock(is_authenticated=False)
    assert private_loc.is_visible_to(anon) is False
