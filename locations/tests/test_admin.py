import pytest
from unittest.mock import MagicMock, patch
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from locations.admin import BaseModelAdmin, LocationAdmin, recalculate_distances
from locations.models import Location
from locations.tests.factories import LocationFactory, UserFactory


def _admin_request(user=None):
  """Return a minimal request suitable for admin views."""
  request = RequestFactory().get('/')
  request.user = user or MagicMock(is_staff=True, is_superuser=True)
  request.session = {}
  request._messages = FallbackStorage(request)
  return request


# ------------------------------------------------------------------ #
#  BaseModelAdmin.save_model
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestBaseModelAdminSaveModel:

  def setup_method(self):
    self.site = AdminSite()
    self.admin = LocationAdmin(Location, self.site)

  def test_sets_user_on_creation_when_not_set(self, db):
    user = UserFactory()
    location = LocationFactory.build(user=None)
    request = _admin_request(user=user)

    self.admin.save_model(request, location, form=MagicMock(), change=False)

    assert location.user == user

  def test_does_not_overwrite_user_on_creation_when_already_set(self, db):
    owner = UserFactory()
    other = UserFactory()
    location = LocationFactory.build(user=owner)
    request = _admin_request(user=other)

    self.admin.save_model(request, location, form=MagicMock(), change=False)

    assert location.user == owner

  def test_does_not_change_user_on_edit(self, db):
    owner = UserFactory()
    other = UserFactory()
    location = LocationFactory(user=owner)
    request = _admin_request(user=other)

    self.admin.save_model(request, location, form=MagicMock(), change=True)

    location.refresh_from_db()
    assert location.user == owner


# ------------------------------------------------------------------ #
#  BaseModelAdmin.get_fieldsets
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestBaseModelAdminGetFieldsets:

  def setup_method(self):
    self.site = AdminSite()
    self.admin = LocationAdmin(Location, self.site)

  def test_appends_system_information_fieldset(self, db):
    request = _admin_request()
    location = LocationFactory()

    fieldsets = self.admin.get_fieldsets(request, obj=location)

    labels = [str(label) for label, _ in fieldsets]
    assert any('system' in label.lower() for label in labels)

  def test_system_fieldset_contains_token_and_dates(self, db):
    request = _admin_request()
    location = LocationFactory()

    fieldsets = self.admin.get_fieldsets(request, obj=location)

    system_fields = []
    for label, options in fieldsets:
      if 'system' in str(label).lower():
        system_fields = options.get('fields', [])
    assert 'token' in system_fields
    assert 'date_created' in system_fields
    assert 'date_modified' in system_fields


# ------------------------------------------------------------------ #
#  BaseModelAdmin.recalculate_fields action
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestRecalculateFieldsAction:

  def setup_method(self):
    self.site = AdminSite()
    self.admin = LocationAdmin(Location, self.site)

  def test_calls_save_on_each_object(self, db):
    LocationFactory()
    LocationFactory()
    request = _admin_request()
    queryset = Location.objects.all()

    with patch.object(Location, 'save') as mock_save:
      self.admin.recalculate_fields(request, queryset)

    assert mock_save.call_count == queryset.count()

  def test_sends_success_message(self, db):
    LocationFactory()
    request = _admin_request()
    queryset = Location.objects.all()

    self.admin.recalculate_fields(request, queryset)

    messages = list(request._messages)
    assert len(messages) == 1
    assert '1' in str(messages[0])


# ------------------------------------------------------------------ #
#  recalculate_distances standalone action
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestRecalculateDistancesAction:

  def test_calls_calculate_distance_on_each_location(self, db):
    LocationFactory()
    LocationFactory()
    request = _admin_request()
    queryset = Location.objects.all()

    with patch.object(Location, 'calculate_distance_to_departure_center') as mock_dist:
      recalculate_distances(MagicMock(), request, queryset)

    assert mock_dist.call_count == 2

  def test_sends_message_with_count(self, db):
    from django.contrib.admin.sites import AdminSite
    LocationFactory()
    request = _admin_request()
    queryset = Location.objects.all()
    admin_instance = LocationAdmin(Location, AdminSite())

    with patch.object(Location, 'calculate_distance_to_departure_center'):
      recalculate_distances(admin_instance, request, queryset)

    messages = list(request._messages)
    assert len(messages) == 1
    assert '1' in str(messages[0])
