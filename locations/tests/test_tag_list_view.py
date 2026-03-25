import pytest
from django.urls import reverse

from locations.tests.factories import TagFactory, LocationFactory


# ------------------------------------------------------------------ #
#  Basic View Tests
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestTagListView:

  def test_view_accessible(self, client):
    url = reverse('locations:tags')
    response = client.get(url)
    assert response.status_code == 200

  def test_uses_correct_template(self, client):
    url = reverse('locations:tags')
    response = client.get(url)
    assert 'tags/tags_list.html' in [t.name for t in response.templates]

  def test_context_contains_tags(self, client):
    TagFactory()
    url = reverse('locations:tags')
    response = client.get(url)
    assert 'tags' in response.context

  def test_context_scope_is_tags(self, client):
    url = reverse('locations:tags')
    response = client.get(url)
    assert response.context['scope'] == 'tags'

  def test_context_includes_active_filters(self, client):
    url = reverse('locations:tags')
    response = client.get(url)
    assert 'active_filters' in response.context

  def test_empty_state_returns_200(self, client):
    url = reverse('locations:tags')
    response = client.get(url)
    assert response.status_code == 200


# ------------------------------------------------------------------ #
#  Visibility / Status Filtering
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestTagListVisibility:

  def test_published_tags_appear(self, client):
    tag = TagFactory(name='Public Tag', status='p', visibility='p')
    url = reverse('locations:tags')
    response = client.get(url)
    names = [t.name for t in response.context['tags']]
    assert 'Public Tag' in names

  def test_unpublished_tags_hidden_from_anonymous(self, client):
    TagFactory(name='Draft Tag', status='c', visibility='p')
    url = reverse('locations:tags')
    response = client.get(url)
    names = [t.name for t in response.context['tags']]
    assert 'Draft Tag' not in names

  def test_community_tags_visible_to_authenticated(self, client, django_user_model):
    user = django_user_model.objects.create_user(username='tester', password='pass')
    client.force_login(user)
    TagFactory(name='Community Tag', status='p', visibility='c')
    url = reverse('locations:tags')
    response = client.get(url)
    names = [t.name for t in response.context['tags']]
    assert 'Community Tag' in names

  def test_community_tags_hidden_from_anonymous(self, client):
    TagFactory(name='Community Tag', status='p', visibility='c')
    url = reverse('locations:tags')
    response = client.get(url)
    names = [t.name for t in response.context['tags']]
    assert 'Community Tag' not in names


# ------------------------------------------------------------------ #
#  Search / Filter
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestTagListSearch:

  def test_filter_by_name(self, client):
    TagFactory(name='Pet Friendly')
    TagFactory(name='Family Friendly')
    url = reverse('locations:tags') + '?name=pet'
    response = client.get(url)
    names = [t.name for t in response.context['tags']]
    assert 'Pet Friendly' in names
    assert 'Family Friendly' not in names

  def test_filter_by_parent_slug(self, client):
    parent = TagFactory(name='Outdoor', parent=None)
    child = TagFactory(name='Hiking', parent=parent)
    other = TagFactory(name='Swimming', parent=None)
    url = reverse('locations:tags') + f'?parent={parent.slug}'
    response = client.get(url)
    names = [t.name for t in response.context['tags']]
    assert 'Hiking' in names
    assert 'Swimming' not in names

  def test_search_no_results_returns_200(self, client):
    TagFactory(name='Hiking')
    url = reverse('locations:tags') + '?name=nonexistent'
    response = client.get(url)
    assert response.status_code == 200
    assert response.context['tags'].count() == 0


# ------------------------------------------------------------------ #
#  Grouping
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestTagListGrouping:

  def test_root_tags_and_child_tags_both_present(self, client):
    parent = TagFactory(name='Outdoor')
    TagFactory(name='Hiking', parent=parent)
    url = reverse('locations:tags')
    response = client.get(url)
    names = [t.name for t in response.context['tags']]
    assert 'Outdoor' in names
    assert 'Hiking' in names

  def test_get_absolute_url_uses_slug(self, db):
    tag = TagFactory(slug='pet-friendly')
    assert 'pet-friendly' in tag.get_absolute_url()
