import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from locations.tests.factories import LocationFactory, UserFactory, MediaFactory, make_image_file


def force_login(client, user):
  user.save()
  client.force_login(user)


def _url(location):
  return reverse('locations:manage_media', kwargs={'slug': location.slug})


def _user_with_permission():
  user = UserFactory()
  perm = Permission.objects.get(codename='change_media')
  user.user_permissions.add(perm)
  return user


# ------------------------------------------------------------------ #
#  Access control
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestManageMediaAccess:

  def test_redirects_anonymous(self, client):
    location = LocationFactory()
    response = client.get(_url(location))
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  def test_redirects_without_permission(self, client):
    user = UserFactory()
    force_login(client, user)
    location = LocationFactory()
    response = client.get(_url(location))
    assert response.status_code in (302, 403)

  def test_accessible_with_permission(self, client):
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    response = client.get(_url(location))
    assert response.status_code == 200

  def test_404_for_unknown_location(self, client):
    user = _user_with_permission()
    force_login(client, user)
    response = client.get(reverse('locations:manage_media', kwargs={'slug': 'no-such-place'}))
    assert response.status_code == 404


# ------------------------------------------------------------------ #
#  GET
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestManageMediaGet:

  def test_uses_correct_template(self, client):
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    response = client.get(_url(location))
    assert 'media/manage_media.html' in [t.name for t in response.templates]

  def test_context_contains_location(self, client):
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    response = client.get(_url(location))
    assert response.context['location'] == location

  def test_renders_existing_media(self, client):
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    MediaFactory(location=location, user=user, title='Sunset View')
    response = client.get(_url(location))
    assert b'Sunset View' in response.content

  def test_ajax_returns_json(self, client):
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    response = client.get(_url(location), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert response.status_code == 200
    data = response.json()
    assert 'payload' in data
    assert 'content' in data['payload']


# ------------------------------------------------------------------ #
#  POST — file upload
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestManageMediaPost:

  def test_upload_creates_media(self, client):
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    from locations.models.Media import Media
    before = Media.objects.filter(location=location).count()
    client.post(_url(location), {'source': make_image_file(), 'visibility': 'p'})
    assert Media.objects.filter(location=location).count() == before + 1

  def test_upload_sets_title(self, client):
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    client.post(_url(location), {'source': make_image_file(), 'title': 'Sunset', 'visibility': 'p'})
    from locations.models.Media import Media
    media = Media.objects.get(location=location)
    assert media.title == 'Sunset'

  def test_invalid_visibility_defaults_to_community(self, client):
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    client.post(_url(location), {'source': make_image_file(), 'visibility': 'invalid'})
    from locations.models.Media import Media
    media = Media.objects.get(location=location)
    assert media.visibility == 'c'

  def test_post_without_file_does_not_create_media(self, client):
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    from locations.models.Media import Media
    client.post(_url(location), {'visibility': 'p'})
    assert Media.objects.filter(location=location).count() == 0

  def test_post_returns_200(self, client):
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    response = client.post(_url(location), {'source': make_image_file(), 'visibility': 'p'})
    assert response.status_code == 200

  def test_duplicate_upload_not_created(self, client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    img = make_image_file()
    client.post(_url(location), {'source': img, 'visibility': 'p'})
    img.seek(0)
    client.post(_url(location), {'source': img, 'visibility': 'p'})
    from locations.models.Media import Media
    assert Media.objects.filter(location=location).count() == 1

  def test_duplicate_upload_returns_warning_message(self, client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user = _user_with_permission()
    force_login(client, user)
    location = LocationFactory()
    img = make_image_file()
    client.post(_url(location), {'source': img, 'visibility': 'p'})
    img.seek(0)
    response = client.post(
      _url(location),
      {'source': img, 'visibility': 'p'},
      HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )
    data = response.json()
    assert 'messages' in data
    assert any(m['level'] == 'warning' for m in data['messages'])
