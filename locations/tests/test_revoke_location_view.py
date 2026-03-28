import json
import pytest
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.urls import reverse

from locations.models.Comment import Comment
from locations.models.Location import Location
from locations.tests.factories import LocationFactory, UserFactory
from locations.views.locations.revoke_location import RevokeLocationView


def _request(method, slug, user, data=None):
  factory = RequestFactory()
  url = f'/location/{slug}/revoke/'
  request = factory.post(url, data or {}) if method == 'post' else factory.get(url)
  request.user = user
  request.session = {}
  request._messages = FallbackStorage(request)
  return request


# ------------------------------------------------------------------ #
#  Permissions
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestRevokeLocationPermissions:

  def test_non_staff_post_redirects(self, db):
    user = UserFactory()
    location = LocationFactory()
    request = _request('post', location.slug, user)
    response = RevokeLocationView.as_view()(request, slug=location.slug)
    assert response.status_code == 302
    assert location.slug in response['Location']

  def test_non_staff_post_adds_warning(self, db):
    user = UserFactory()
    location = LocationFactory()
    request = _request('post', location.slug, user)
    RevokeLocationView.as_view()(request, slug=location.slug)
    msgs = list(get_messages(request))
    assert any('not allowed' in str(m).lower() for m in msgs)

  def test_non_staff_post_does_not_change_status(self, db):
    user = UserFactory()
    location = LocationFactory(status='p')
    request = _request('post', location.slug, user)
    RevokeLocationView.as_view()(request, slug=location.slug)
    location.refresh_from_db()
    assert location.status == 'p'


# ------------------------------------------------------------------ #
#  GET — returns modal HTML as JSON
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestRevokeLocationGet:

  def test_get_returns_json(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory()
    request = _request('get', location.slug, staff)
    response = RevokeLocationView.as_view()(request, slug=location.slug)
    assert response.status_code == 200
    data = json.loads(response.content)
    assert 'payload' in data
    assert 'content' in data['payload']

  def test_get_content_contains_form(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory()
    request = _request('get', location.slug, staff)
    response = RevokeLocationView.as_view()(request, slug=location.slug)
    data = json.loads(response.content)
    assert '<form' in data['payload']['content']


# ------------------------------------------------------------------ #
#  POST — revoke (published → revoked)
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestRevokeLocationRevoke:

  def test_sets_status_to_revoked(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='p')
    request = _request('post', location.slug, staff)
    RevokeLocationView.as_view()(request, slug=location.slug)
    location.refresh_from_db()
    assert location.status == 'r'

  def test_redirects_to_detail_page(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='p')
    request = _request('post', location.slug, staff)
    response = RevokeLocationView.as_view()(request, slug=location.slug)
    assert response.status_code == 302
    assert location.slug in response['Location']

  def test_adds_success_message(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='p')
    request = _request('post', location.slug, staff)
    RevokeLocationView.as_view()(request, slug=location.slug)
    msgs = list(get_messages(request))
    assert any('revoked' in str(m).lower() for m in msgs)

  def test_with_reason_creates_comment(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='p')
    request = _request('post', location.slug, staff, {'reason': 'Permanently closed.'})
    RevokeLocationView.as_view()(request, slug=location.slug)
    ct = ContentType.objects.get_for_model(location)
    comments = Comment.objects.filter(content_type=ct, object_id=location.pk)
    assert comments.count() == 1
    assert comments.first().text == 'Permanently closed.'

  def test_comment_has_community_visibility(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='p')
    request = _request('post', location.slug, staff, {'reason': 'Closed.'})
    RevokeLocationView.as_view()(request, slug=location.slug)
    ct = ContentType.objects.get_for_model(location)
    comment = Comment.objects.get(content_type=ct, object_id=location.pk)
    assert comment.visibility == 'c'

  def test_comment_attributed_to_staff_user(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='p')
    request = _request('post', location.slug, staff, {'reason': 'Closed.'})
    RevokeLocationView.as_view()(request, slug=location.slug)
    ct = ContentType.objects.get_for_model(location)
    comment = Comment.objects.get(content_type=ct, object_id=location.pk)
    assert comment.user == staff

  def test_without_reason_creates_no_comment(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='p')
    request = _request('post', location.slug, staff)
    RevokeLocationView.as_view()(request, slug=location.slug)
    ct = ContentType.objects.get_for_model(location)
    assert Comment.objects.filter(content_type=ct, object_id=location.pk).count() == 0

  def test_blank_reason_creates_no_comment(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='p')
    request = _request('post', location.slug, staff, {'reason': '   '})
    RevokeLocationView.as_view()(request, slug=location.slug)
    ct = ContentType.objects.get_for_model(location)
    assert Comment.objects.filter(content_type=ct, object_id=location.pk).count() == 0


# ------------------------------------------------------------------ #
#  POST — republish (revoked → published)
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestRevokeLocationRepublish:

  def test_sets_status_to_published(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='r')
    request = _request('post', location.slug, staff)
    RevokeLocationView.as_view()(request, slug=location.slug)
    location.refresh_from_db()
    assert location.status == 'p'

  def test_redirects_to_detail_page(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='r')
    request = _request('post', location.slug, staff)
    response = RevokeLocationView.as_view()(request, slug=location.slug)
    assert response.status_code == 302
    assert location.slug in response['Location']

  def test_adds_success_message(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='r')
    request = _request('post', location.slug, staff)
    RevokeLocationView.as_view()(request, slug=location.slug)
    msgs = list(get_messages(request))
    assert any('republished' in str(m).lower() for m in msgs)

  def test_republish_creates_no_comment(self, db):
    staff = UserFactory(is_staff=True)
    location = LocationFactory(status='r')
    request = _request('post', location.slug, staff, {'reason': 'Looks fine now.'})
    RevokeLocationView.as_view()(request, slug=location.slug)
    ct = ContentType.objects.get_for_model(location)
    assert Comment.objects.filter(content_type=ct, object_id=location.pk).count() == 0
