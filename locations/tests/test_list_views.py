import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from locations.tests.factories import (
    LocationFactory, UserFactory, ListFactory, ListItemFactory,
)


def force_login(client, user):
  """UserFactory uses skip_postgeneration_save=True, so set_password() is not
  persisted to DB. Django 6 validates HASH_SESSION_KEY against the DB password
  on every request — if they differ the session is flushed. Calling save()
  first syncs the in-memory hash to the DB."""
  user.save()
  client.force_login(user)


def make_member_user():
  user = UserFactory()
  user.user_permissions.add(Permission.objects.get(codename='add_list'))
  return user


# ------------------------------------------------------------------ #
#  ListListView  (lists/)
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestListListView:

  def test_accessible_anonymous(self, client):
    response = client.get(reverse('locations:lists'))
    assert response.status_code == 200

  def test_uses_correct_template(self, client):
    response = client.get(reverse('locations:lists'))
    assert 'lists/lists_list.html' in [t.name for t in response.templates]

  def test_context_contains_lists(self, client):
    response = client.get(reverse('locations:lists'))
    assert 'lists' in response.context

  def test_context_scope_is_lists(self, client):
    response = client.get(reverse('locations:lists'))
    assert response.context['scope'] == 'lists'

  def test_published_public_list_appears(self, client):
    lst = ListFactory(name='Camping Europe', status='p', visibility='p')
    response = client.get(reverse('locations:lists'))
    assert lst in response.context['lists']

  def test_unpublished_list_hidden_from_anonymous(self, client):
    lst = ListFactory(name='Draft List', status='c', visibility='p')
    response = client.get(reverse('locations:lists'))
    assert lst not in response.context['lists']

  def test_community_list_visible_to_authenticated(self, client):
    user = UserFactory()
    force_login(client, user)
    lst = ListFactory(status='p', visibility='c')
    response = client.get(reverse('locations:lists'))
    assert lst in response.context['lists']

  def test_community_list_hidden_from_anonymous(self, client):
    lst = ListFactory(status='p', visibility='c')
    response = client.get(reverse('locations:lists'))
    assert lst not in response.context['lists']

  def test_empty_state_returns_200(self, client):
    response = client.get(reverse('locations:lists'))
    assert response.status_code == 200


# ------------------------------------------------------------------ #
#  ListDetailView  (lists/<slug>/)
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestListDetailView:

  def test_accessible_for_public_list(self, client):
    lst = ListFactory(status='p', visibility='p')
    response = client.get(reverse('locations:list_detail', kwargs={'slug': lst.slug}))
    assert response.status_code == 200

  def test_uses_correct_template(self, client):
    lst = ListFactory(status='p', visibility='p')
    response = client.get(reverse('locations:list_detail', kwargs={'slug': lst.slug}))
    assert 'lists/list_detail.html' in [t.name for t in response.templates]

  def test_context_contains_list(self, client):
    lst = ListFactory(status='p', visibility='p')
    response = client.get(reverse('locations:list_detail', kwargs={'slug': lst.slug}))
    assert response.context['list'] == lst

  def test_context_contains_items(self, client):
    lst = ListFactory(status='p', visibility='p')
    item = ListItemFactory(list=lst, order=0)
    response = client.get(reverse('locations:list_detail', kwargs={'slug': lst.slug}))
    assert item in response.context['items']

  def test_context_scope_is_list_detail(self, client):
    lst = ListFactory(status='p', visibility='p')
    response = client.get(reverse('locations:list_detail', kwargs={'slug': lst.slug}))
    assert response.context['scope'] == 'list_detail'

  def test_items_ordered_by_order(self, client):
    lst = ListFactory(status='p', visibility='p')
    ListItemFactory(list=lst, order=2)
    ListItemFactory(list=lst, order=0)
    ListItemFactory(list=lst, order=1)
    response = client.get(reverse('locations:list_detail', kwargs={'slug': lst.slug}))
    orders = [item.order for item in response.context['items']]
    assert orders == sorted(orders)

  def test_private_list_denied_to_anonymous(self, client):
    lst = ListFactory(status='p', visibility='q')
    response = client.get(reverse('locations:list_detail', kwargs={'slug': lst.slug}))
    assert response.status_code == 403

  def test_private_list_accessible_to_owner(self, client):
    user = UserFactory()
    force_login(client, user)
    lst = ListFactory(status='p', visibility='q', user=user)
    response = client.get(reverse('locations:list_detail', kwargs={'slug': lst.slug}))
    assert response.status_code == 200

  def test_404_for_unknown_slug(self, client):
    response = client.get(reverse('locations:list_detail', kwargs={'slug': 'no-such-list'}))
    assert response.status_code == 404


# ------------------------------------------------------------------ #
#  ManageListsView  (lists/manage/<slug>/)
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestManageListsView:

  def _url(self, location):
    return reverse('locations:manage_lists', kwargs={'slug': location.slug})

  def test_redirects_anonymous_to_login(self, client):
    location = LocationFactory()
    response = client.get(self._url(location))
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  def test_accessible_to_authenticated(self, client):
    user = make_member_user()
    force_login(client, user)
    location = LocationFactory()
    response = client.get(self._url(location))
    assert response.status_code == 200

  def test_uses_correct_template(self, client):
    user = make_member_user()
    force_login(client, user)
    location = LocationFactory()
    response = client.get(self._url(location))
    assert 'lists/manage_lists.html' in [t.name for t in response.templates]

  def test_context_contains_location(self, client):
    user = make_member_user()
    force_login(client, user)
    location = LocationFactory()
    response = client.get(self._url(location))
    assert response.context['location'] == location

  def test_context_contains_location_lists(self, client):
    user = make_member_user()
    force_login(client, user)
    location = LocationFactory()
    lst = ListFactory(status='p', visibility='p')
    ListItemFactory(list=lst, location=location)
    response = client.get(self._url(location))
    assert lst in response.context['location_lists']

  def test_context_contains_user_lists(self, client):
    user = make_member_user()
    force_login(client, user)
    location = LocationFactory()
    lst = ListFactory(status='p', visibility='p', user=user)
    ListItemFactory(list=lst, location=location)
    response = client.get(self._url(location))
    assert lst in response.context['user_lists']

  def test_404_for_unknown_location(self, client):
    user = make_member_user()
    force_login(client, user)
    response = client.get(reverse('locations:manage_lists', kwargs={'slug': 'no-such-place'}))
    assert response.status_code == 404

  def test_ajax_returns_json(self, client):
    user = make_member_user()
    force_login(client, user)
    location = LocationFactory()
    response = client.get(
      self._url(location),
      HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )
    assert response.status_code == 200
    data = response.json()
    assert 'payload' in data
    assert 'content' in data['payload']
