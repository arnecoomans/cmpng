import pytest
from django.urls import reverse

from locations.models import Tag
from locations.tests.factories import LocationFactory, TagFactory, UserFactory


def _url(tag):
  return reverse('locations:delete_tag', kwargs={'slug': tag.slug})


def _post(client, tag):
  return client.post(_url(tag))


def _staff(client):
  user = UserFactory(is_staff=True)
  user.save()
  client.force_login(user)
  return user


# ------------------------------------------------------------------ #
#  Permissions
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestDeleteTagViewPermissions:

  def test_anonymous_redirected_to_login(self, client):
    tag = TagFactory()
    response = _post(client, tag)
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  def test_non_staff_forbidden(self, client):
    user = UserFactory()
    user.save()
    client.force_login(user)
    tag = TagFactory()
    response = _post(client, tag)
    assert response.status_code == 403

  def test_staff_can_access(self, client):
    _staff(client)
    tag = TagFactory()
    response = _post(client, tag)
    assert response.status_code == 302

  def test_get_not_allowed(self, client):
    _staff(client)
    tag = TagFactory()
    response = client.get(_url(tag))
    assert response.status_code == 405


# ------------------------------------------------------------------ #
#  Successful soft-delete
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestDeleteTagViewSuccess:

  def test_unassigned_tag_status_set_to_x(self, client):
    _staff(client)
    tag = TagFactory()
    _post(client, tag)
    tag.refresh_from_db()
    assert tag.status == 'x'

  def test_redirects_to_dashboard(self, client):
    _staff(client)
    tag = TagFactory()
    response = _post(client, tag)
    assert response.status_code == 302
    assert response['Location'] == reverse('locations:staff_dashboard')

  def test_success_message_includes_tag_name(self, client):
    _staff(client)
    tag = TagFactory(name='Lakeside')
    response = client.post(_url(tag), follow=True)
    messages = [str(m) for m in response.context['messages']]
    assert any('deleted' in m.lower() and 'Lakeside' in m for m in messages)

  def test_success_message_includes_parent_name(self, client):
    _staff(client)
    parent = TagFactory(name='Water')
    tag = TagFactory(name='Lakeside', parent=parent)
    response = client.post(_url(tag), follow=True)
    messages = [str(m) for m in response.context['messages']]
    assert any('Water' in m and 'Lakeside' in m for m in messages)

  def test_tag_with_only_revoked_locations_is_deletable(self, client):
    _staff(client)
    tag = TagFactory()
    loc = LocationFactory(status='r')
    loc.tags.add(tag)
    _post(client, tag)
    tag.refresh_from_db()
    assert tag.status == 'x'


# ------------------------------------------------------------------ #
#  Blocked when tag has locations
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestDeleteTagViewBlocked:

  def test_assigned_tag_not_soft_deleted(self, client):
    _staff(client)
    tag = TagFactory()
    loc = LocationFactory()
    loc.tags.add(tag)
    _post(client, tag)
    tag.refresh_from_db()
    assert tag.status == 'p'

  def test_blocked_redirects_to_dashboard(self, client):
    _staff(client)
    tag = TagFactory()
    loc = LocationFactory()
    loc.tags.add(tag)
    response = _post(client, tag)
    assert response.status_code == 302
    assert response['Location'] == reverse('locations:staff_dashboard')

  def test_error_message_added(self, client):
    _staff(client)
    tag = TagFactory()
    loc = LocationFactory()
    loc.tags.add(tag)
    response = client.post(_url(tag), follow=True)
    messages = [str(m) for m in response.context['messages']]
    assert any('cannot' in m.lower() for m in messages)
