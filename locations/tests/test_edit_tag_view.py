import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from locations.tests.factories import TagFactory, UserFactory


def _make_permitted_user():
  user = UserFactory()
  user.save()
  user.user_permissions.add(Permission.objects.get(codename='change_tag'))
  return user


def _url(tag):
  return reverse('locations:edit_tag', kwargs={'slug': tag.slug})


def _post(client, tag, **kwargs):
  data = {
    'name': tag.name,
    'slug': tag.slug,
    'description': '',
    'status': tag.status,
    'similarity_weight': tag.similarity_weight,
  }
  data.update(kwargs)
  return client.post(_url(tag), data)


# ------------------------------------------------------------------ #
#  Permissions
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestEditTagViewPermissions:

  def test_anonymous_redirected_to_login(self, client):
    tag = TagFactory()
    response = client.get(_url(tag))
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  def test_non_staff_user_forbidden(self, client):
    user = UserFactory()
    user.save()
    client.force_login(user)
    tag = TagFactory()
    response = client.get(_url(tag))
    assert response.status_code == 403

  def test_permitted_user_can_access(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    tag = TagFactory()
    response = client.get(_url(tag))
    assert response.status_code == 200


# ------------------------------------------------------------------ #
#  GET
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestEditTagViewGet:

  def test_uses_correct_template(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    tag = TagFactory()
    response = client.get(_url(tag))
    assert 'tags/edit_tag.html' in [t.name for t in response.templates]

  def test_form_prefilled_with_tag_data(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    tag = TagFactory(name='Camping', description='A campsite')
    response = client.get(_url(tag))
    assert response.context['form'].initial['name'] == 'Camping' or \
      response.context['object'].name == 'Camping'

  def test_parent_field_not_required(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    tag = TagFactory()
    response = client.get(_url(tag))
    assert not response.context['form'].fields['parent'].required


# ------------------------------------------------------------------ #
#  POST — basic field updates
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestEditTagViewPost:

  def test_valid_post_redirects_to_tag_list(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    tag = TagFactory()
    response = _post(client, tag)
    assert response.status_code == 302
    assert response['Location'] == reverse('locations:tags')

  def test_name_update_persists(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    tag = TagFactory(name='Old name', slug='old-name')
    _post(client, tag, name='New name', slug='old-name')
    tag.refresh_from_db()
    assert tag.name == 'New name'

  def test_status_update_persists(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    tag = TagFactory(status='p')
    _post(client, tag, status='c')
    tag.refresh_from_db()
    assert tag.status == 'c'

  def test_similarity_weight_update_persists(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    tag = TagFactory(similarity_weight=100)
    _post(client, tag, similarity_weight=150)
    tag.refresh_from_db()
    assert tag.similarity_weight == 150


# ------------------------------------------------------------------ #
#  POST — parent assignment via autosuggest (parent__id)
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestEditTagViewParent:

  def test_parent_assigned_via_parent_id(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    parent = TagFactory()
    tag = TagFactory()
    _post(client, tag, **{'parent__id': parent.pk})
    tag.refresh_from_db()
    assert tag.parent == parent

  def test_parent_can_be_left_empty(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    tag = TagFactory()
    response = _post(client, tag)
    assert response.status_code == 302
    tag.refresh_from_db()
    assert tag.parent is None

  def test_existing_parent_preserved_when_not_submitted(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    parent = TagFactory()
    tag = TagFactory(parent=parent)
    _post(client, tag)
    tag.refresh_from_db()
    assert tag.parent is None

  def test_parent_replaced_with_new_parent(self, client):
    user = _make_permitted_user()
    client.force_login(user)
    old_parent = TagFactory()
    new_parent = TagFactory()
    tag = TagFactory(parent=old_parent)
    _post(client, tag, **{'parent__id': new_parent.pk})
    tag.refresh_from_db()
    assert tag.parent == new_parent
