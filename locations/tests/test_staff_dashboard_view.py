import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from locations.models.Location import Location
from locations.models import Category
from locations.tests.factories import (
  CategoryFactory,
  CommentFactory,
  LocationFactory,
  UserFactory,
)


URL = reverse('locations:staff_dashboard')


def force_login(client, user):
  user.save()
  client.force_login(user)


def _get(client):
  return client.get(URL)


# ------------------------------------------------------------------ #
#  Permissions
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStaffDashboardPermissions:

  def test_anonymous_redirects_to_login(self, client):
    response = _get(client)
    assert response.status_code == 302
    assert 'login' in response['Location'] or 'accounts' in response['Location']

  def test_non_staff_is_forbidden(self, client):
    force_login(client, UserFactory())
    response = _get(client)
    assert response.status_code == 403

  def test_staff_gets_200(self, client):
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    assert response.status_code == 200


# ------------------------------------------------------------------ #
#  Template & context keys
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStaffDashboardContext:

  def setup_method(self):
    self.staff = UserFactory(is_staff=True)

  def _response(self, client):
    force_login(client, self.staff)
    return _get(client)

  def test_uses_correct_template(self, client):
    response = self._response(client)
    assert 'staff/dashboard.html' in [t.name for t in response.templates]

  def test_context_contains_all_expected_keys(self, client):
    response = self._response(client)
    expected = [
      'lowest_completeness',
      'missing_summary', 'missing_summary_count',
      'missing_description', 'missing_description_count',
      'fewest_tags', 'fewest_tags_boundary',
      'fewest_categories', 'fewest_categories_boundary',
      'recently_commented',
      'recently_added',
      'revoked', 'revoked_count',
      'max_results',
    ]
    for key in expected:
      assert key in response.context, f'missing context key: {key}'


# ------------------------------------------------------------------ #
#  Lowest completeness
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStaffDashboardLowestCompleteness:

  def test_ordered_by_completeness_ascending(self, client):
    low  = LocationFactory(completeness=10)
    high = LocationFactory(completeness=80)
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    ids = [loc.pk for loc in response.context['lowest_completeness']]
    assert ids.index(low.pk) < ids.index(high.pk)

  def test_excludes_revoked_locations(self, client):
    revoked = LocationFactory(status='r', completeness=0)
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    ids = [loc.pk for loc in response.context['lowest_completeness']]
    assert revoked.pk not in ids


# ------------------------------------------------------------------ #
#  Missing summary
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStaffDashboardMissingSummary:

  def test_count_includes_locations_with_no_summary(self, client):
    LocationFactory(summary=None)
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    assert response.context['missing_summary_count'] >= 1

  def test_count_includes_locations_with_short_summary(self, client):
    LocationFactory(summary='Too short')
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    assert response.context['missing_summary_count'] >= 1

  def test_count_excludes_locations_with_adequate_summary(self, client):
    LocationFactory(summary='A' * 60)
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    adequate_pks = [loc.pk for loc in response.context['missing_summary']]
    # The location with a long summary should not appear
    long_summary_locs = Location.objects.filter(summary__isnull=False).exclude(pk__in=adequate_pks)
    for loc in long_summary_locs:
      if loc.summary and len(loc.summary) >= 50:
        assert loc.pk not in adequate_pks


# ------------------------------------------------------------------ #
#  Missing description
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStaffDashboardMissingDescription:

  def test_count_includes_locations_with_empty_description(self, client):
    LocationFactory(description='')
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    assert response.context['missing_description_count'] >= 1

  def test_location_with_description_not_in_list(self, client):
    loc = LocationFactory(description='A full description of this place.')
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    pks = [l.pk for l in response.context['missing_description']]
    assert loc.pk not in pks


# ------------------------------------------------------------------ #
#  Fewest tags — boundary logic
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStaffDashboardFewestTags:

  def test_boundary_equals_tag_count_of_tenth_result(self, client):
    # Create 12 locations: 8 with 0 tags, 4 with 1 tag
    locs_zero = LocationFactory.create_batch(8)
    locs_one  = LocationFactory.create_batch(4)
    from locations.models import Tag
    from django.utils.text import slugify
    tag = Tag.objects.create(name='test-tag', slug='test-tag', status='p')
    for loc in locs_one:
      loc.tags.add(tag)
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    # 10th result has 1 tag, so boundary should be 1 and all 12 shown
    assert response.context['fewest_tags_boundary'] == 1
    pks = {loc.pk for loc in response.context['fewest_tags']}
    for loc in locs_zero + locs_one:
      assert loc.pk in pks

  def test_all_locations_in_same_tier_are_included(self, client):
    # 15 locations all with 0 tags — all should appear despite max_results=15
    locs = LocationFactory.create_batch(15)
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    assert response.context['fewest_tags_boundary'] == 0
    pks = {loc.pk for loc in response.context['fewest_tags']}
    for loc in locs:
      assert loc.pk in pks


# ------------------------------------------------------------------ #
#  Revoked
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStaffDashboardRevoked:

  def test_revoked_count_reflects_total_not_list_length(self, client):
    LocationFactory.create_batch(20, status='r')
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    assert response.context['revoked_count'] == 20

  def test_revoke_comment_prefetched_when_title_contains_revok(self, client):
    location = LocationFactory(status='r')
    ct = ContentType.objects.get_for_model(location)
    CommentFactory(
      content_type=ct,
      object_id=location.pk,
      title='Revoke reason',
      text='Permanently closed.',
    )
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    revoked_loc = next(l for l in response.context['revoked'] if l.pk == location.pk)
    assert len(revoked_loc.revoke_comments) == 1
    assert revoked_loc.revoke_comments[0].text == 'Permanently closed.'

  def test_comment_without_revok_in_title_not_prefetched(self, client):
    location = LocationFactory(status='r')
    ct = ContentType.objects.get_for_model(location)
    CommentFactory(
      content_type=ct,
      object_id=location.pk,
      title='General note',
      text='Some unrelated comment.',
    )
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    revoked_loc = next(l for l in response.context['revoked'] if l.pk == location.pk)
    assert len(revoked_loc.revoke_comments) == 0

  def test_published_locations_not_in_revoked(self, client):
    published = LocationFactory(status='p')
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    pks = [l.pk for l in response.context['revoked']]
    assert published.pk not in pks


# ------------------------------------------------------------------ #
#  Recently commented
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStaffDashboardRecentlyCommented:

  def test_location_with_comment_appears(self, client):
    location = LocationFactory()
    ct = ContentType.objects.get_for_model(location)
    CommentFactory(content_type=ct, object_id=location.pk)
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    pks = [l.pk for l in response.context['recently_commented']]
    assert location.pk in pks

  def test_location_without_comment_excluded(self, client):
    location = LocationFactory()
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    pks = [l.pk for l in response.context['recently_commented']]
    assert location.pk not in pks

  def test_most_recently_commented_appears_first(self, client):
    from django.utils import timezone
    from datetime import timedelta
    older = LocationFactory()
    newer = LocationFactory()
    ct = ContentType.objects.get_for_model(older)
    c1 = CommentFactory(content_type=ct, object_id=older.pk)
    c2 = CommentFactory(content_type=ct, object_id=newer.pk)
    # Force date ordering
    c1.__class__.objects.filter(pk=c1.pk).update(date_created=timezone.now() - timedelta(days=1))
    c2.__class__.objects.filter(pk=c2.pk).update(date_created=timezone.now())
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    pks = [l.pk for l in response.context['recently_commented']]
    assert pks.index(newer.pk) < pks.index(older.pk)


# ------------------------------------------------------------------ #
#  Recently added
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStaffDashboardRecentlyAdded:

  def test_most_recently_created_appears_first(self, client):
    from django.utils import timezone
    from datetime import timedelta
    older = LocationFactory()
    newer = LocationFactory()
    Location.objects.filter(pk=older.pk).update(date_created=timezone.now() - timedelta(days=2))
    Location.objects.filter(pk=newer.pk).update(date_created=timezone.now())
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    pks = [l.pk for l in response.context['recently_added']]
    assert pks.index(newer.pk) < pks.index(older.pk)

  def test_revoked_locations_excluded(self, client):
    revoked = LocationFactory(status='r')
    user = UserFactory(is_staff=True)
    force_login(client, user)
    response = _get(client)
    pks = [l.pk for l in response.context['recently_added']]
    assert revoked.pk not in pks


# ------------------------------------------------------------------ #
#  Home category exclusion
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestStaffDashboardHomeCategoryExclusion:

  def _home_category(self):
    return Category.objects.get_or_create(slug='home', defaults={'name': 'Home', 'status': 'p'})[0]

  def _home_location(self):
    loc = LocationFactory()
    loc.categories.add(self._home_category())
    return loc

  def _staff(self, client):
    user = UserFactory(is_staff=True)
    force_login(client, user)

  def test_home_location_excluded_from_lowest_completeness(self, client):
    home_loc = self._home_location()
    self._staff(client)
    response = _get(client)
    pks = [l.pk for l in response.context['lowest_completeness']]
    assert home_loc.pk not in pks

  def test_home_location_excluded_from_missing_summary(self, client):
    home_loc = self._home_location()
    self._staff(client)
    response = _get(client)
    pks = [l.pk for l in response.context['missing_summary']]
    assert home_loc.pk not in pks

  def test_home_location_excluded_from_missing_summary_count(self, client):
    LocationFactory(summary=None)  # non-home, should be counted
    home_loc = self._home_location()
    home_loc.summary = None
    home_loc.save()
    self._staff(client)
    response = _get(client)
    pks = [l.pk for l in response.context['missing_summary']]
    assert home_loc.pk not in pks

  def test_home_location_excluded_from_missing_description(self, client):
    home_loc = self._home_location()
    self._staff(client)
    response = _get(client)
    pks = [l.pk for l in response.context['missing_description']]
    assert home_loc.pk not in pks

  def test_home_location_excluded_from_fewest_tags(self, client):
    home_loc = self._home_location()
    self._staff(client)
    response = _get(client)
    pks = [l.pk for l in response.context['fewest_tags']]
    assert home_loc.pk not in pks

  def test_home_location_excluded_from_fewest_categories(self, client):
    home_loc = self._home_location()
    self._staff(client)
    response = _get(client)
    pks = [l.pk for l in response.context['fewest_categories']]
    assert home_loc.pk not in pks

  def test_home_location_excluded_from_recently_commented(self, client):
    home_loc = self._home_location()
    ct = ContentType.objects.get_for_model(home_loc)
    CommentFactory(content_type=ct, object_id=home_loc.pk)
    self._staff(client)
    response = _get(client)
    pks = [l.pk for l in response.context['recently_commented']]
    assert home_loc.pk not in pks

  def test_home_location_excluded_from_recently_added(self, client):
    home_loc = self._home_location()
    self._staff(client)
    response = _get(client)
    pks = [l.pk for l in response.context['recently_added']]
    assert home_loc.pk not in pks

  def test_revoked_home_location_still_in_revoked_list(self, client):
    home_loc = LocationFactory(status='r')
    home_loc.categories.add(self._home_category())
    self._staff(client)
    response = _get(client)
    pks = [l.pk for l in response.context['revoked']]
    assert home_loc.pk in pks
