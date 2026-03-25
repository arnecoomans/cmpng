"""
Tests for BaseModel.filter_status().

Uses Location as the concrete BaseModel subclass.
"""
import pytest
from unittest.mock import Mock
from django.contrib.auth.models import AnonymousUser

from locations.models import Location
from locations.tests.factories import LocationFactory, UserFactory


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def anon_request():
  req = Mock()
  req.user = AnonymousUser()
  return req


def auth_request(user):
  req = Mock()
  req.user = user
  return req


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def regular_user(db):
  return UserFactory()


@pytest.fixture
def staff_user(db):
  user = UserFactory()
  user.is_staff = True
  user.save()
  return user


@pytest.fixture
def owner(db):
  return UserFactory()


@pytest.fixture
def published(owner):
  return LocationFactory(status='p', user=owner)


@pytest.fixture
def concept(owner):
  return LocationFactory(status='c', user=owner)


@pytest.fixture
def revoked(owner):
  return LocationFactory(status='r', user=owner)


@pytest.fixture
def deleted(owner):
  return LocationFactory(status='x', user=owner)


# ------------------------------------------------------------------ #
#  Unauthenticated access
# ------------------------------------------------------------------ #

class TestFilterStatusAnonymous:

  def test_published_visible_to_anon(self, db, published):
    qs = Location.filter_status(Location.objects.all(), request=anon_request())
    assert published in qs

  def test_concept_hidden_from_anon(self, db, concept):
    qs = Location.filter_status(Location.objects.all(), request=anon_request())
    assert concept not in qs

  def test_revoked_hidden_from_anon(self, db, revoked):
    qs = Location.filter_status(Location.objects.all(), request=anon_request())
    assert revoked not in qs

  def test_deleted_hidden_from_anon(self, db, deleted):
    qs = Location.filter_status(Location.objects.all(), request=anon_request())
    assert deleted not in qs

  def test_no_request_shows_only_published(self, db, published, concept):
    qs = Location.filter_status(Location.objects.all(), request=None)
    assert published in qs
    assert concept not in qs


# ------------------------------------------------------------------ #
#  Authenticated non-staff
# ------------------------------------------------------------------ #

class TestFilterStatusAuthenticated:

  def test_published_visible(self, db, published, regular_user):
    qs = Location.filter_status(Location.objects.all(), request=auth_request(regular_user))
    assert published in qs

  def test_own_concept_visible(self, db, owner):
    own_concept = LocationFactory(status='c', user=owner)
    qs = Location.filter_status(Location.objects.all(), request=auth_request(owner))
    assert own_concept in qs

  def test_other_concept_hidden(self, db, concept, regular_user):
    qs = Location.filter_status(Location.objects.all(), request=auth_request(regular_user))
    assert concept not in qs

  def test_revoked_hidden_from_regular_user(self, db, revoked, regular_user):
    qs = Location.filter_status(Location.objects.all(), request=auth_request(regular_user))
    assert revoked not in qs

  def test_deleted_hidden_from_regular_user(self, db, deleted, regular_user):
    qs = Location.filter_status(Location.objects.all(), request=auth_request(regular_user))
    assert deleted not in qs


# ------------------------------------------------------------------ #
#  Staff access
# ------------------------------------------------------------------ #

class TestFilterStatusStaff:

  def test_published_visible_to_staff(self, db, published, staff_user):
    qs = Location.filter_status(Location.objects.all(), request=auth_request(staff_user))
    assert published in qs

  def test_concept_visible_to_staff(self, db, concept, staff_user):
    qs = Location.filter_status(Location.objects.all(), request=auth_request(staff_user))
    assert concept in qs

  def test_revoked_visible_to_staff(self, db, revoked, staff_user):
    qs = Location.filter_status(Location.objects.all(), request=auth_request(staff_user))
    assert revoked in qs

  def test_deleted_hidden_from_staff(self, db, deleted, staff_user):
    qs = Location.filter_status(Location.objects.all(), request=auth_request(staff_user))
    assert deleted not in qs
