import csv
import io
import zipfile
from datetime import date

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from locations.models.Visits import Visits
from locations.models.Preferences import UserPreferences
from locations.tests.factories import (
  UserFactory,
  LocationFactory,
  VisitsFactory,
  CommentFactory,
  MediaFactory,
  ListFactory,
  ListItemFactory,
)


def force_login(client, user):
  user.save()
  client.force_login(user)


def _zip_filenames(response):
  buf = io.BytesIO(response.content)
  with zipfile.ZipFile(buf) as zf:
    return zf.namelist()


def _read_csv(response, filename):
  buf = io.BytesIO(response.content)
  with zipfile.ZipFile(buf) as zf:
    return list(csv.reader(io.StringIO(zf.read(filename).decode('utf-8'))))


# ------------------------------------------------------------------ #
#  Access control
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestExportDataAccessControl:

  def test_get_redirects_anonymous(self, client):
    response = client.get(reverse('locations:export_data'))
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  def test_post_redirects_anonymous(self, client):
    response = client.post(reverse('locations:export_data'))
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  def test_get_accessible_to_authenticated(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.get(reverse('locations:export_data'))
    assert response.status_code == 200


# ------------------------------------------------------------------ #
#  GET — form rendering
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestExportDataGet:

  def test_context_contains_sections(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.get(reverse('locations:export_data'))
    assert 'sections' in response.context

  def test_all_six_sections_present(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.get(reverse('locations:export_data'))
    keys = [key for key, _ in response.context['sections']]
    assert set(keys) == {'profile', 'visits', 'comments', 'locations', 'media', 'lists'}


# ------------------------------------------------------------------ #
#  POST — ZIP response
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestExportDataZipResponse:

  def test_response_content_type_is_zip(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'visits': 'on'})
    assert response['Content-Type'] == 'application/zip'

  def test_content_disposition_contains_username_and_date(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'visits': 'on'})
    disposition = response['Content-Disposition']
    assert user.username in disposition
    assert date.today().isoformat() in disposition
    assert 'attachment' in disposition

  def test_response_is_valid_zip(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'visits': 'on'})
    buf = io.BytesIO(response.content)
    assert zipfile.is_zipfile(buf)


# ------------------------------------------------------------------ #
#  POST — section selection
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestExportDataSectionSelection:

  def test_all_sections_selected_produces_all_six_csvs(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {
      'profile': 'on', 'visits': 'on', 'comments': 'on', 'locations': 'on', 'media': 'on', 'lists': 'on',
    })
    assert set(_zip_filenames(response)) == {
      'profile.csv', 'visits.csv', 'comments.csv', 'locations.csv', 'media.csv', 'lists.csv',
    }

  def test_single_section_produces_one_csv(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'visits': 'on'})
    assert _zip_filenames(response) == ['visits.csv']

  def test_no_selection_falls_back_to_all_sections(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {})
    assert set(_zip_filenames(response)) == {
      'profile.csv', 'visits.csv', 'comments.csv', 'locations.csv', 'media.csv', 'lists.csv',
    }


# ------------------------------------------------------------------ #
#  POST — data isolation
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestExportDataIsolation:

  def test_visits_only_contains_own_user(self, client):
    user = UserFactory()
    other = UserFactory()
    location = LocationFactory()
    VisitsFactory(user=user, location=location)
    VisitsFactory(user=other, location=location)
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'visits': 'on'})
    rows = _read_csv(response, 'visits.csv')
    # header + 1 data row (own visit only)
    assert len(rows) == 2

  def test_locations_only_contains_own_user(self, client):
    user = UserFactory()
    other = UserFactory()
    LocationFactory(user=user)
    LocationFactory(user=other)
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'locations': 'on'})
    rows = _read_csv(response, 'locations.csv')
    assert len(rows) == 2  # header + 1

  def test_lists_only_contains_own_user(self, client):
    user = UserFactory()
    other = UserFactory()
    lst = ListFactory(user=user)
    other_lst = ListFactory(user=other)
    ListItemFactory(list=lst)
    ListItemFactory(list=other_lst)
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'lists': 'on'})
    rows = _read_csv(response, 'lists.csv')
    assert len(rows) == 2  # header + 1


# ------------------------------------------------------------------ #
#  POST — CSV contents
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestExportDataCsvContents:

  def test_visits_csv_contains_location_name(self, client):
    user = UserFactory()
    location = LocationFactory(name='Test Campsite')
    VisitsFactory(user=user, location=location)
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'visits': 'on'})
    rows = _read_csv(response, 'visits.csv')
    assert rows[1][0] == 'Test Campsite'

  def test_visits_csv_recommendation_label_not_integer(self, client):
    user = UserFactory()
    location = LocationFactory()
    VisitsFactory(user=user, location=location, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'visits': 'on'})
    rows = _read_csv(response, 'visits.csv')
    assert rows[1][-1] == 'recommended'

  def test_visits_csv_empty_recommendation_when_unrated(self, client):
    user = UserFactory()
    location = LocationFactory()
    VisitsFactory(user=user, location=location, recommendation=None)
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'visits': 'on'})
    rows = _read_csv(response, 'visits.csv')
    assert rows[1][-1] == ''

  def test_comments_csv_includes_revoked(self, client):
    user = UserFactory()
    location = LocationFactory()
    ct = ContentType.objects.get_for_model(location)
    CommentFactory(user=user, content_type=ct, object_id=location.pk, status='r')
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'comments': 'on'})
    rows = _read_csv(response, 'comments.csv')
    assert len(rows) == 2  # header + revoked comment
    assert rows[1][4] == 'r'

  def test_locations_csv_contains_correct_columns(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'locations': 'on'})
    rows = _read_csv(response, 'locations.csv')
    assert rows[0] == ['name', 'description', 'address', 'status', 'visibility', 'date_created', 'date_modified']

  def test_lists_csv_contains_location_name(self, client):
    user = UserFactory()
    location = LocationFactory(name='Nice Spot')
    lst = ListFactory(user=user)
    ListItemFactory(list=lst, location=location, order=1)
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'lists': 'on'})
    rows = _read_csv(response, 'lists.csv')
    assert rows[1][2] == 'Nice Spot'


# ------------------------------------------------------------------ #
#  POST — empty data
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestExportDataEmptyData:

  def test_visits_csv_with_no_visits_has_only_header(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'visits': 'on'})
    rows = _read_csv(response, 'visits.csv')
    assert len(rows) == 1
    assert rows[0][0] == 'location'

  def test_all_sections_with_no_data_produces_valid_zip(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {
      'profile': 'on', 'visits': 'on', 'comments': 'on', 'locations': 'on', 'media': 'on', 'lists': 'on',
    })
    assert zipfile.is_zipfile(io.BytesIO(response.content))


# ------------------------------------------------------------------ #
#  POST — profile CSV
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestExportDataProfileCsv:

  def test_profile_csv_contains_correct_columns(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'profile': 'on'})
    rows = _read_csv(response, 'profile.csv')
    assert rows[0] == ['name', 'username', 'email', 'language', 'home', 'family', 'favorites']

  def test_profile_csv_contains_username(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'profile': 'on'})
    rows = _read_csv(response, 'profile.csv')
    assert rows[1][1] == user.username

  def test_profile_csv_contains_email(self, client):
    user = UserFactory()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'profile': 'on'})
    rows = _read_csv(response, 'profile.csv')
    assert rows[1][2] == user.email

  def test_profile_csv_contains_home_location_name(self, client):
    user = UserFactory()
    home = LocationFactory(name='Home Base')
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    prefs.home = home
    prefs.save()
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'profile': 'on'})
    rows = _read_csv(response, 'profile.csv')
    assert rows[1][4] == 'Home Base'

  def test_profile_csv_contains_favorites(self, client):
    user = UserFactory()
    fav = LocationFactory(name='Favourite Spot')
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    prefs.favorites.add(fav)
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'profile': 'on'})
    rows = _read_csv(response, 'profile.csv')
    assert 'Favourite Spot' in rows[1][6]

  def test_profile_csv_contains_family_usernames(self, client):
    user = UserFactory()
    family_member = UserFactory()
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    prefs.family.add(family_member)
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'profile': 'on'})
    rows = _read_csv(response, 'profile.csv')
    assert family_member.username in rows[1][5]

  def test_profile_csv_works_without_preferences(self, client):
    user = UserFactory()
    # No UserPreferences created
    force_login(client, user)
    response = client.post(reverse('locations:export_data'), {'profile': 'on'})
    rows = _read_csv(response, 'profile.csv')
    assert len(rows) == 2  # header + one row
    assert rows[1][1] == user.username
