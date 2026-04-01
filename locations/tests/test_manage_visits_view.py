import pytest
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

from django.contrib.auth.models import Permission

from locations.models import Visits
from locations.tests.factories import LocationFactory, UserFactory
from locations.views.visits.manage_visits import ManageVisitsView


def _make_member_user():
  user = UserFactory()
  user.user_permissions.add(Permission.objects.get(codename='add_visits'))
  return user


def _get(url='/', user=None, ajax=False, **kwargs):
  rf = RequestFactory()
  headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'} if ajax else {}
  request = rf.get(url, **kwargs, **headers)
  request.user = user or UserFactory.build()
  request.session = {}
  request._messages = FallbackStorage(request)
  return request


# ------------------------------------------------------------------ #
#  get_queryset
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestManageVisitsViewQueryset:

  def test_returns_only_current_user_visits(self, db):
    user = UserFactory()
    other = UserFactory()
    location = LocationFactory()
    Visits.objects.create(user=user, location=location, year=2024)
    Visits.objects.create(user=other, location=location, year=2024)

    request = _get(user=user)
    view = ManageVisitsView()
    view.request = request
    view.kwargs = {}

    qs = view.get_queryset()

    assert all(v.user == user for v in qs)
    assert qs.count() == 1

  def test_filters_by_slug_when_provided(self, db):
    user = UserFactory()
    loc_a = LocationFactory()
    loc_b = LocationFactory()
    Visits.objects.create(user=user, location=loc_a, year=2024)
    Visits.objects.create(user=user, location=loc_b, year=2024)

    request = _get(user=user)
    view = ManageVisitsView()
    view.request = request
    view.kwargs = {'slug': loc_a.slug}

    qs = view.get_queryset()

    assert qs.count() == 1
    assert qs.first().location == loc_a


# ------------------------------------------------------------------ #
#  get_context_data
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestManageVisitsViewContext:

  def test_context_scope_is_visits(self, db):
    user = _make_member_user()
    request = _get(user=user)

    response = ManageVisitsView.as_view()(request)

    assert response.context_data['scope'] == 'visits'

  def test_context_location_is_none_without_slug(self, db):
    user = _make_member_user()
    request = _get(user=user)

    response = ManageVisitsView.as_view()(request)

    assert response.context_data['location'] is None

  def test_context_location_set_when_slug_provided(self, db):
    user = _make_member_user()
    location = LocationFactory()
    request = _get(user=user)

    response = ManageVisitsView.as_view()(request, slug=location.slug)

    assert response.context_data['location'] == location

  def test_context_months_present(self, db):
    user = _make_member_user()
    request = _get(user=user)

    response = ManageVisitsView.as_view()(request)

    assert 'months' in response.context_data


# ------------------------------------------------------------------ #
#  get — normal vs AJAX
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestManageVisitsViewGet:

  def test_normal_request_returns_200(self, db):
    user = _make_member_user()
    request = _get(user=user)

    response = ManageVisitsView.as_view()(request)

    assert response.status_code == 200

  def test_ajax_request_returns_json(self, db):
    from unittest.mock import patch
    user = _make_member_user()
    request = _get(user=user, ajax=True)

    with patch('locations.views.visits.manage_visits.render_to_string', return_value='<html>'):
      response = ManageVisitsView.as_view()(request)

    assert response.status_code == 200
    assert 'application/json' in response['Content-Type']

  def test_ajax_response_contains_payload(self, db):
    import json
    from unittest.mock import patch
    user = _make_member_user()
    request = _get(user=user, ajax=True)

    with patch('locations.views.visits.manage_visits.render_to_string', return_value='<html>'):
      response = ManageVisitsView.as_view()(request)

    data = json.loads(response.content)
    assert 'payload' in data
    assert 'content' in data['payload']
