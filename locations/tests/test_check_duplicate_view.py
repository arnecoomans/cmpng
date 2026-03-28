import json
import pytest
from django.urls import reverse

from locations.tests.factories import LocationFactory, UserFactory


URL = reverse('locations:check_duplicate')


def force_login(client, user):
  user.save()
  client.force_login(user)


def _get(client, q):
  return client.get(URL, {'q': q})


def _json(response):
  return json.loads(response.content)


# ------------------------------------------------------------------ #
#  Authentication
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCheckDuplicateAuth:

  def test_anonymous_redirects_to_login(self, client):
    response = _get(client, 'test')
    assert response.status_code == 302
    assert '/login' in response['Location'] or 'accounts' in response['Location']

  def test_authenticated_returns_200(self, client):
    user = UserFactory()
    force_login(client, user)
    response = _get(client, 'test')
    assert response.status_code == 200


# ------------------------------------------------------------------ #
#  Query length guard
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCheckDuplicateQueryGuard:

  def test_empty_query_returns_empty_matches(self, client):
    user = UserFactory()
    force_login(client, user)
    response = _get(client, '')
    assert _json(response)['matches'] == []

  def test_single_char_returns_empty_matches(self, client):
    user = UserFactory()
    force_login(client, user)
    response = _get(client, 'a')
    assert _json(response)['matches'] == []

  def test_two_chars_triggers_search(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Ab camping', user=user)
    response = _get(client, 'Ab')
    assert len(_json(response)['matches']) == 1


# ------------------------------------------------------------------ #
#  Scope — staff vs. non-staff
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCheckDuplicateScope:

  def test_non_staff_sees_only_own_locations(self, client):
    user = UserFactory()
    other = UserFactory()
    force_login(client, user)
    LocationFactory(name='Shared Name', user=user)
    LocationFactory(name='Shared Name', user=other)
    response = _get(client, 'Shared Name')
    assert len(_json(response)['matches']) == 1

  def test_staff_sees_all_users_locations(self, client):
    staff = UserFactory(is_staff=True)
    other = UserFactory()
    force_login(client, staff)
    LocationFactory(name='Shared Name', user=staff)
    LocationFactory(name='Shared Name', user=other)
    response = _get(client, 'Shared Name')
    assert len(_json(response)['matches']) == 2


# ------------------------------------------------------------------ #
#  All statuses are searched
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCheckDuplicateStatuses:

  def test_finds_published_location(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Test Camping', user=user, status='p')
    data = _json(_get(client, 'Test Camping'))
    statuses = [m['status'] for m in data['matches']]
    assert 'p' in statuses

  def test_finds_revoked_location(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Test Camping', user=user, status='r')
    data = _json(_get(client, 'Test Camping'))
    statuses = [m['status'] for m in data['matches']]
    assert 'r' in statuses

  def test_finds_concept_location(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Test Camping', user=user, status='c')
    data = _json(_get(client, 'Test Camping'))
    statuses = [m['status'] for m in data['matches']]
    assert 'c' in statuses

  def test_finds_deleted_location(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Test Camping', user=user, status='x')
    data = _json(_get(client, 'Test Camping'))
    statuses = [m['status'] for m in data['matches']]
    assert 'x' in statuses


# ------------------------------------------------------------------ #
#  Response shape
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCheckDuplicateResponseShape:

  def test_published_match_has_url(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Test Camping', user=user, status='p', slug='test-camping')
    match = _json(_get(client, 'Test Camping'))['matches'][0]
    assert match['url'] is not None
    assert 'test-camping' in match['url']

  def test_revoked_match_has_no_url(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Test Camping', user=user, status='r')
    match = _json(_get(client, 'Test Camping'))['matches'][0]
    assert match['url'] is None

  def test_revoked_match_has_revoke_url(self, client):
    user = UserFactory()
    force_login(client, user)
    loc = LocationFactory(name='Test Camping', user=user, status='r')
    match = _json(_get(client, 'Test Camping'))['matches'][0]
    assert match['revoke_url'] is not None
    assert loc.slug in match['revoke_url']

  def test_published_match_has_no_revoke_url(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Test Camping', user=user, status='p')
    match = _json(_get(client, 'Test Camping'))['matches'][0]
    assert match['revoke_url'] is None

  def test_status_label_is_lowercase_string(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Test Camping', user=user, status='p')
    match = _json(_get(client, 'Test Camping'))['matches'][0]
    assert match['status_label'] == match['status_label'].lower()

  def test_match_includes_slug(self, client):
    user = UserFactory()
    force_login(client, user)
    loc = LocationFactory(name='Test Camping', user=user)
    match = _json(_get(client, 'Test Camping'))['matches'][0]
    assert match['slug'] == loc.slug


# ------------------------------------------------------------------ #
#  can_unrevoke flag
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCheckDuplicateCanUnrevoke:

  def test_can_unrevoke_true_for_own_revoked(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Test Camping', user=user, status='r')
    match = _json(_get(client, 'Test Camping'))['matches'][0]
    assert match['can_unrevoke'] is True

  def test_can_unrevoke_false_for_published(self, client):
    user = UserFactory()
    force_login(client, user)
    LocationFactory(name='Test Camping', user=user, status='p')
    match = _json(_get(client, 'Test Camping'))['matches'][0]
    assert match['can_unrevoke'] is False

  def test_can_unrevoke_true_for_staff_on_others_revoked(self, client):
    staff = UserFactory(is_staff=True)
    other = UserFactory()
    force_login(client, staff)
    LocationFactory(name='Test Camping', user=other, status='r')
    match = _json(_get(client, 'Test Camping'))['matches'][0]
    assert match['can_unrevoke'] is True
