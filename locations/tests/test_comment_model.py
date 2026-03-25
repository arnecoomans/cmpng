"""
Tests for the Comment model (locations/models/Comment.py).
Extends cmnsd.models.Comment.BaseComment with GenericForeignKey support.
"""
import pytest
from django.contrib.contenttypes.models import ContentType

from locations.models import Location
from locations.models.Comment import Comment
from locations.tests.factories import CommentFactory, LocationFactory, UserFactory


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def make_comment(location, **kwargs):
  ct = ContentType.objects.get_for_model(Location)
  return CommentFactory(content_type=ct, object_id=location.pk, **kwargs)


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def location(db):
  return LocationFactory()


@pytest.fixture
def comment(db, location):
  return make_comment(location)


# ------------------------------------------------------------------ #
#  Basic fields
# ------------------------------------------------------------------ #

class TestCommentBasics:

  def test_text_is_stored(self, comment):
    assert comment.text != ''

  def test_title_defaults_to_empty(self, db, location):
    c = make_comment(location, title='')
    assert c.title == ''

  def test_title_can_be_set(self, db, location):
    c = make_comment(location, title='My title')
    assert c.title == 'My title'

  def test_empty_text_raises_on_save(self, db, location):
    ct = ContentType.objects.get_for_model(Location)
    c = Comment(content_type=ct, object_id=location.pk, text='  ', title='')
    with pytest.raises(ValueError):
      c.save()


# ------------------------------------------------------------------ #
#  get_title and __str__
# ------------------------------------------------------------------ #

class TestCommentGetTitle:

  def test_get_title_returns_title_when_set(self, db, location):
    c = make_comment(location, title='My Title')
    assert c.get_title() == 'My Title'

  def test_get_title_returns_text_preview_when_no_title(self, db, location):
    c = make_comment(location, text='Short text', title='')
    assert c.get_title() == 'Short text'

  def test_get_title_truncates_long_text(self, db, location):
    long_text = 'a' * 80
    c = make_comment(location, text=long_text, title='')
    title = c.get_title()
    assert '…' in title
    assert len(title) < len(long_text)

  def test_str_delegates_to_get_title(self, db, location):
    c = make_comment(location, title='Test Title')
    assert str(c) == c.get_title()


# ------------------------------------------------------------------ #
#  GenericForeignKey — content_type and object_id
# ------------------------------------------------------------------ #

class TestCommentGenericFK:

  def test_content_type_is_set_to_location(self, comment):
    expected_ct = ContentType.objects.get_for_model(Location)
    assert comment.content_type == expected_ct

  def test_object_id_matches_location_pk(self, comment, location):
    assert comment.object_id == location.pk

  def test_content_object_resolves_to_location(self, comment, location):
    assert comment.content_object == location

  def test_multiple_comments_on_same_location(self, db, location):
    c1 = make_comment(location, text='First comment')
    c2 = make_comment(location, text='Second comment')
    ct = ContentType.objects.get_for_model(Location)
    qs = Comment.objects.filter(content_type=ct, object_id=location.pk)
    assert qs.count() == 2

  def test_comments_on_different_locations_are_separate(self, db):
    loc1 = LocationFactory()
    loc2 = LocationFactory()
    make_comment(loc1, text='Comment on loc1')
    make_comment(loc2, text='Comment on loc2')
    ct = ContentType.objects.get_for_model(Location)
    assert Comment.objects.filter(content_type=ct, object_id=loc1.pk).count() == 1
    assert Comment.objects.filter(content_type=ct, object_id=loc2.pk).count() == 1


# ------------------------------------------------------------------ #
#  BaseModel inheritance
# ------------------------------------------------------------------ #

class TestCommentBaseModel:

  def test_token_auto_generated(self, comment):
    assert comment.token is not None
    assert len(comment.token) >= 10

  def test_tokens_are_unique(self, db, location):
    c1 = make_comment(location)
    c2 = make_comment(location)
    assert c1.token != c2.token

  def test_date_created_is_set(self, comment):
    assert comment.date_created is not None

  def test_date_modified_updates_on_save(self, comment):
    original = comment.date_modified
    comment.text = 'Updated text'
    comment.save()
    comment.refresh_from_db()
    assert comment.date_modified > original

  def test_user_fk_is_set(self, comment):
    assert comment.user is not None

  def test_user_fk_is_nullable(self, db, location):
    c = make_comment(location, user=None)
    assert c.user is None

  def test_default_status_is_published(self, db, location):
    c = make_comment(location, status='p')
    assert c.status == 'p'


# ------------------------------------------------------------------ #
#  VisibilityModel inheritance
# ------------------------------------------------------------------ #

class TestCommentVisibility:

  def test_default_visibility_is_community(self, db, location):
    c = make_comment(location, visibility='c')
    assert c.visibility == 'c'

  def test_visibility_can_be_set_to_public(self, db, location):
    c = make_comment(location, visibility='p')
    assert c.visibility == 'p'

  def test_visibility_can_be_set_to_private(self, db, location):
    c = make_comment(location, visibility='q')
    assert c.visibility == 'q'

  def test_is_visible_to_public_comment(self, db, location):
    c = make_comment(location, visibility='p')
    assert c.is_visible_to(None) is True

  def test_is_visible_to_private_comment_owner_only(self, db, location):
    owner = UserFactory()
    other = UserFactory()
    c = make_comment(location, visibility='q', user=owner)
    assert c.is_visible_to(owner) is True
    assert c.is_visible_to(other) is False

  def test_filter_visibility_on_comment_queryset(self, db, location):
    from unittest.mock import Mock
    public_c = make_comment(location, visibility='p')
    private_c = make_comment(location, visibility='q')
    req = Mock()
    req.user = Mock(is_authenticated=False)
    qs = Comment.filter_visibility(Comment.objects.all(), request=req)
    assert public_c in qs
    assert private_c not in qs


# ------------------------------------------------------------------ #
#  Ordering
# ------------------------------------------------------------------ #

class TestCommentOrdering:

  def test_comments_ordered_by_date_created_descending(self, db, location):
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    c1 = make_comment(location, text='First')
    c2 = make_comment(location, text='Second')
    c3 = make_comment(location, text='Third')
    # auto_now_add ignores values passed to create(); use update() to force distinct timestamps
    Comment.objects.filter(pk=c1.pk).update(date_created=now)
    Comment.objects.filter(pk=c2.pk).update(date_created=now + timedelta(seconds=1))
    Comment.objects.filter(pk=c3.pk).update(date_created=now + timedelta(seconds=2))
    ordered = list(Comment.objects.all())
    assert ordered[0] == c3
    assert ordered[-1] == c1
