"""Tests for Location.calculate_completeness() and completeness_hints()."""
import pytest
from django.contrib.contenttypes.models import ContentType

from locations.models import Visits
from locations.tests.factories import (
  CategoryFactory, CommentFactory, LinkFactory, ListItemFactory,
  LocationFactory, MediaFactory, TagFactory, UserFactory,
)


def _add_visit(location, user):
  Visits.objects.create(user=user, location=location, year=2024)


def _ct(location):
  return ContentType.objects.get_for_model(location)


@pytest.mark.django_db
class TestCompletenessBaseScores:

  def test_empty_location_scores_zero(self):
    location = LocationFactory(
      address=None, summary=None, description='',
    )
    location.calculate_completeness()
    assert location.completeness == 0

  def test_address_adds_points(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    location.address = '1 Rue de la Paix, Paris'
    location.save()
    location.calculate_completeness()
    assert location.completeness > base

  def test_summary_adds_points(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    location.summary = 'A great campsite.'
    location.save()
    location.calculate_completeness()
    assert location.completeness > base

  def test_description_adds_points(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    location.description = 'Longer description text.'
    location.save()
    location.calculate_completeness()
    assert location.completeness > base

  def test_link_adds_points(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    LinkFactory(location=location)
    location.calculate_completeness()
    assert location.completeness > base

  def test_one_category_adds_points(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    location.categories.add(CategoryFactory())
    location.calculate_completeness()
    assert location.completeness > base

  def test_two_categories_scores_higher_than_one(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.categories.add(CategoryFactory())
    location.calculate_completeness()
    one_cat = location.completeness

    location.categories.add(CategoryFactory())
    location.calculate_completeness()
    assert location.completeness > one_cat

  def test_one_tag_adds_points(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    location.tags.add(TagFactory())
    location.calculate_completeness()
    assert location.completeness > base

  def test_two_tags_scores_higher_than_one(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.tags.add(TagFactory())
    location.calculate_completeness()
    one_tag = location.completeness

    location.tags.add(TagFactory())
    location.calculate_completeness()
    assert location.completeness > one_tag

  def test_public_media_adds_points(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    MediaFactory(location=location, visibility='p', status='p')
    location.calculate_completeness()
    assert location.completeness > base

  def test_community_media_adds_points(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    MediaFactory(location=location, visibility='c', status='p')
    location.calculate_completeness()
    assert location.completeness > base

  def test_private_media_does_not_add_points(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    MediaFactory(location=location, visibility='q', status='p')
    location.calculate_completeness()
    assert location.completeness == base

  def test_summary_worth_more_than_description(self):
    location_s = LocationFactory(summary='A summary.', description='', address=None)
    location_d = LocationFactory(summary=None, description='A description.', address=None)
    location_s.calculate_completeness()
    location_d.calculate_completeness()
    assert location_s.completeness > location_d.completeness


@pytest.mark.django_db
class TestCompletenessBonuses:

  def test_visit_adds_bonus(self):
    user = UserFactory()
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    _add_visit(location, user)
    location.calculate_completeness()
    assert location.completeness > base

  def test_list_item_adds_bonus(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    ListItemFactory(location=location)
    location.calculate_completeness()
    assert location.completeness > base

  def test_published_comment_adds_bonus(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    CommentFactory(content_type=_ct(location), object_id=location.pk, status='p')
    location.calculate_completeness()
    assert location.completeness > base

  def test_draft_comment_does_not_add_bonus(self):
    location = LocationFactory(address=None, summary=None, description='')
    location.calculate_completeness()
    base = location.completeness

    CommentFactory(content_type=_ct(location), object_id=location.pk, status='c')
    location.calculate_completeness()
    assert location.completeness == base

  def test_score_capped_at_100(self):
    user = UserFactory()
    location = LocationFactory(
      address='1 Rue de la Paix',
      summary='Great spot',
      description='Long description',
    )
    LinkFactory(location=location)
    location.categories.add(CategoryFactory(), CategoryFactory())
    location.tags.add(TagFactory(), TagFactory())
    MediaFactory(location=location, visibility='p', status='p')
    ListItemFactory(location=location)
    _add_visit(location, user)
    CommentFactory(content_type=_ct(location), object_id=location.pk, status='p')
    location.calculate_completeness()
    assert location.completeness <= 100


@pytest.mark.django_db
class TestCompletenessHints:

  def test_hints_returns_list_of_tuples(self):
    location = LocationFactory()
    hints = location.completeness_hints()
    assert isinstance(hints, list)
    assert all(isinstance(h, tuple) and len(h) == 2 for h in hints)

  def test_done_status_when_criterion_met(self):
    location = LocationFactory(address='1 Main St', summary='Good spot')
    statuses = dict(location.completeness_hints())
    assert any(s == 'done' for s in statuses.values())

  def test_missing_status_when_criterion_absent(self):
    location = LocationFactory(address=None, summary=None, description='')
    statuses = dict(location.completeness_hints())
    assert any(s == 'missing' for s in statuses.values())

  def test_bonus_status_when_visited(self):
    user = UserFactory()
    location = LocationFactory()
    _add_visit(location, user)
    hints = dict(location.completeness_hints())
    assert any(s == 'bonus' for s in hints.values())

  def test_size_bonus_hint_shown_only_when_applicable(self):
    location = LocationFactory()
    hint_labels = [str(label) for label, _ in location.completeness_hints()]
    # Without size-applicable categories, size hint should not appear
    has_size_hint = any('size' in label.lower() for label in hint_labels)
    assert not has_size_hint
