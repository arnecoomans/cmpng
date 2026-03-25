import pytest
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType

from locations.tests.factories import CommentFactory, LocationFactory, UserFactory


def make_comment(location, **kwargs):
  """Helper: create a comment attached to a location."""
  ct = ContentType.objects.get_for_model(location)
  return CommentFactory(content_type=ct, object_id=location.pk, **kwargs)


# ------------------------------------------------------------------ #
#  Basic View Tests
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCommentListView:

  def test_view_accessible_anonymous(self, client):
    url = reverse('locations:comments')
    response = client.get(url)
    assert response.status_code == 200

  def test_uses_correct_template(self, client):
    url = reverse('locations:comments')
    response = client.get(url)
    assert 'comments/comments_list.html' in [t.name for t in response.templates]

  def test_context_contains_comments(self, client):
    location = LocationFactory()
    make_comment(location)
    url = reverse('locations:comments')
    response = client.get(url)
    assert 'comments' in response.context

  def test_context_scope_is_comments(self, client):
    url = reverse('locations:comments')
    response = client.get(url)
    assert response.context['scope'] == 'comments'

  def test_context_includes_active_filters(self, client):
    url = reverse('locations:comments')
    response = client.get(url)
    assert 'active_filters' in response.context

  def test_empty_state_returns_200(self, client):
    url = reverse('locations:comments')
    response = client.get(url)
    assert response.status_code == 200


# ------------------------------------------------------------------ #
#  Visibility / Status Filtering
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCommentListVisibility:

  def test_public_comments_visible_to_anonymous(self, client):
    location = LocationFactory()
    make_comment(location, title='Public Comment', status='p', visibility='p')
    url = reverse('locations:comments')
    response = client.get(url)
    titles = [c.title for c in response.context['comments']]
    assert 'Public Comment' in titles

  def test_unpublished_comments_hidden(self, client):
    location = LocationFactory()
    make_comment(location, title='Draft Comment', status='c', visibility='p')
    url = reverse('locations:comments')
    response = client.get(url)
    titles = [c.title for c in response.context['comments']]
    assert 'Draft Comment' not in titles

  def test_community_comments_visible_to_authenticated(self, client, django_user_model):
    user = django_user_model.objects.create_user(username='tester', password='pass')
    client.force_login(user)
    location = LocationFactory()
    make_comment(location, title='Community Comment', status='p', visibility='c')
    url = reverse('locations:comments')
    response = client.get(url)
    titles = [c.title for c in response.context['comments']]
    assert 'Community Comment' in titles

  def test_community_comments_hidden_from_anonymous(self, client):
    location = LocationFactory()
    make_comment(location, title='Community Comment', status='p', visibility='c')
    url = reverse('locations:comments')
    response = client.get(url)
    titles = [c.title for c in response.context['comments']]
    assert 'Community Comment' not in titles

  def test_multiple_comments_from_different_locations(self, client):
    loc1 = LocationFactory()
    loc2 = LocationFactory()
    make_comment(loc1, title='Comment A', status='p', visibility='p')
    make_comment(loc2, title='Comment B', status='p', visibility='p')
    url = reverse('locations:comments')
    response = client.get(url)
    titles = [c.title for c in response.context['comments']]
    assert 'Comment A' in titles
    assert 'Comment B' in titles


# ------------------------------------------------------------------ #
#  Search / Filter
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCommentListSearch:

  def test_search_by_title(self, client):
    location = LocationFactory()
    make_comment(location, title='Great camping spot', status='p', visibility='p')
    make_comment(location, title='Bad experience', status='p', visibility='p')
    url = reverse('locations:comments') + '?title=great'
    response = client.get(url)
    titles = [c.title for c in response.context['comments']]
    assert 'Great camping spot' in titles
    assert 'Bad experience' not in titles

  def test_search_by_text(self, client):
    location = LocationFactory()
    make_comment(location, text='Amazing views from the hilltop', status='p', visibility='p')
    make_comment(location, text='Terrible noise all night', status='p', visibility='p')
    url = reverse('locations:comments') + '?text=amazing'
    response = client.get(url)
    texts = [c.text for c in response.context['comments']]
    assert 'Amazing views from the hilltop' in texts
    assert 'Terrible noise all night' not in texts

  def test_search_no_results_returns_200(self, client):
    location = LocationFactory()
    make_comment(location, title='Some comment', status='p', visibility='p')
    url = reverse('locations:comments') + '?title=nonexistent'
    response = client.get(url)
    assert response.status_code == 200
    assert response.context['comments'].count() == 0


# ------------------------------------------------------------------ #
#  Ordering
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCommentListOrdering:

  def test_default_ordering_newest_first(self, client):
    location = LocationFactory()
    c1 = make_comment(location, title='Older', status='p', visibility='p')
    c2 = make_comment(location, title='Newer', status='p', visibility='p')
    url = reverse('locations:comments')
    response = client.get(url)
    comments = list(response.context['comments'])
    # Newer comment (higher pk) should come first given -date_created ordering
    assert comments[0].pk >= comments[-1].pk


# ------------------------------------------------------------------ #
#  Pagination
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCommentListPagination:

  def test_pagination_20_per_page(self, client):
    location = LocationFactory()
    for _ in range(25):
      make_comment(location, status='p', visibility='p')
    url = reverse('locations:comments')
    response = client.get(url)
    assert len(response.context['comments']) == 20

  def test_second_page_has_remaining(self, client):
    location = LocationFactory()
    for _ in range(25):
      make_comment(location, status='p', visibility='p')
    url = reverse('locations:comments') + '?page=2'
    response = client.get(url)
    assert len(response.context['comments']) == 5
