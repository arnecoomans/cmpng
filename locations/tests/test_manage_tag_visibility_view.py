import json

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse

from locations.models import Tag
from locations.tests.factories import TagFactory, UserFactory
from locations.views.tags.manage_tag_visibility import ManageTagVisibilityView


def _make_staff_user():
  user = UserFactory()
  user.save()
  user.user_permissions.add(Permission.objects.get(codename='change_tag'))
  return user


# ------------------------------------------------------------------ #
#  Permissions
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestManageTagVisibilityPermissions:

  def test_anonymous_redirected_to_login(self, client):
    response = client.get(reverse('locations:manage_tag_visibility'))
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  def test_user_without_permission_denied(self, db):
    user = UserFactory()
    user.save()
    rf = RequestFactory()
    request = rf.get('/tags/manage-visibility/')
    request.user = user
    with pytest.raises(PermissionDenied):
      ManageTagVisibilityView.as_view()(request)

  def test_staff_user_can_access(self, client):
    user = _make_staff_user()
    client.force_login(user)
    response = client.get(reverse('locations:manage_tag_visibility'))
    assert response.status_code == 200


# ------------------------------------------------------------------ #
#  GET — columns
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestManageTagVisibilityGet:

  def test_uses_correct_template(self, client):
    user = _make_staff_user()
    client.force_login(user)
    response = client.get(reverse('locations:manage_tag_visibility'))
    assert 'tags/manage_tag_visibility.html' in [t.name for t in response.templates]

  def test_context_contains_columns(self, client):
    user = _make_staff_user()
    client.force_login(user)
    response = client.get(reverse('locations:manage_tag_visibility'))
    assert 'columns' in response.context

  def test_context_columns_keyed_by_visibility_choices(self, client):
    user = _make_staff_user()
    client.force_login(user)
    response = client.get(reverse('locations:manage_tag_visibility'))
    expected_keys = {v for v, _ in Tag.visibility_choices}
    assert set(response.context['columns'].keys()) == expected_keys

  def test_tags_sorted_into_correct_column(self, client):
    user = _make_staff_user()
    client.force_login(user)
    public_tag = TagFactory(visibility='p')
    private_tag = TagFactory(visibility='q')
    response = client.get(reverse('locations:manage_tag_visibility'))
    columns = response.context['columns']
    assert public_tag in columns['p']
    assert private_tag in columns['q']

  def test_context_contains_visibility_labels(self, client):
    user = _make_staff_user()
    client.force_login(user)
    response = client.get(reverse('locations:manage_tag_visibility'))
    assert 'visibility_labels' in response.context


# ------------------------------------------------------------------ #
#  POST — update visibility
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestManageTagVisibilityPost:

  def _post_json(self, client, payload):
    return client.post(
      reverse('locations:manage_tag_visibility'),
      data=json.dumps(payload),
      content_type='application/json',
    )

  def test_valid_update_returns_ok(self, client):
    user = _make_staff_user()
    client.force_login(user)
    tag = TagFactory(visibility='p')
    response = self._post_json(client, {'tag_id': tag.pk, 'visibility': 'c'})
    assert response.status_code == 200
    assert response.json() == {'ok': True}

  def test_valid_update_persists_to_db(self, client):
    user = _make_staff_user()
    client.force_login(user)
    tag = TagFactory(visibility='p')
    self._post_json(client, {'tag_id': tag.pk, 'visibility': 'c'})
    tag.refresh_from_db()
    assert tag.visibility == 'c'

  def test_invalid_visibility_returns_400(self, client):
    user = _make_staff_user()
    client.force_login(user)
    tag = TagFactory()
    response = self._post_json(client, {'tag_id': tag.pk, 'visibility': 'invalid'})
    assert response.status_code == 400
    assert 'error' in response.json()

  def test_nonexistent_tag_returns_404(self, client):
    user = _make_staff_user()
    client.force_login(user)
    response = self._post_json(client, {'tag_id': 99999, 'visibility': 'p'})
    assert response.status_code == 404

  def test_invalid_json_returns_400(self, client):
    user = _make_staff_user()
    client.force_login(user)
    response = client.post(
      reverse('locations:manage_tag_visibility'),
      data='not-json',
      content_type='application/json',
    )
    assert response.status_code == 400

  def test_post_without_permission_denied(self, db):
    user = UserFactory()
    user.save()
    rf = RequestFactory()
    request = rf.post(
      '/tags/manage-visibility/',
      data=json.dumps({'tag_id': 1, 'visibility': 'p'}),
      content_type='application/json',
    )
    request.user = user
    with pytest.raises(PermissionDenied):
      ManageTagVisibilityView.as_view()(request)
