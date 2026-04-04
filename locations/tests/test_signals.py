from unittest.mock import patch

import pytest

from locations.signals import listitem_saved, location_saved, visit_saved
from locations.tests.factories import CategoryFactory, LocationFactory, UserFactory


@pytest.mark.django_db
class TestSignalsRawSkip:
  """Signals must not recalculate completeness during fixture loading (raw=True)."""

  def test_location_saved_raw_skips_recalculate(self):
    location = LocationFactory()
    with patch.object(location, 'calculate_completeness') as mock:
      location_saved(sender=None, instance=location, raw=True, update_fields=None)
    mock.assert_not_called()

  def test_location_saved_not_raw_recalculates(self):
    location = LocationFactory()
    with patch.object(location, 'calculate_completeness') as mock:
      location_saved(sender=None, instance=location, raw=False, update_fields=None)
    mock.assert_called_once()

  def test_visit_saved_raw_skips_recalculate(self, db):
    from locations.models import Visits
    user = UserFactory()
    user.save()
    location = LocationFactory()
    visit = Visits(user=user, location=location, year=2024)
    visit.save()
    with patch('locations.signals._recalculate') as mock:
      visit_saved(sender=None, instance=visit, raw=True)
    mock.assert_not_called()

  def test_visit_saved_not_raw_recalculates(self, db):
    from locations.models import Visits
    user = UserFactory()
    user.save()
    location = LocationFactory()
    visit = Visits(user=user, location=location, year=2024)
    visit.save()
    with patch('locations.signals._recalculate') as mock:
      visit_saved(sender=None, instance=visit, raw=False)
    mock.assert_called_once_with(visit.location)

  def test_listitem_saved_raw_skips_recalculate(self, db):
    from locations.models import List, ListItem
    user = UserFactory()
    user.save()
    location = LocationFactory()
    lst = List.objects.create(name='Test', user=user, status='p')
    item = ListItem(list=lst, location=location)
    item.save()
    with patch('locations.signals._recalculate') as mock:
      listitem_saved(sender=None, instance=item, raw=True)
    mock.assert_not_called()

  def test_listitem_saved_not_raw_recalculates(self, db):
    from locations.models import List, ListItem
    user = UserFactory()
    user.save()
    location = LocationFactory()
    lst = List.objects.create(name='Test', user=user, status='p')
    item = ListItem(list=lst, location=location)
    item.save()
    with patch('locations.signals._recalculate') as mock:
      listitem_saved(sender=None, instance=item, raw=False)
    mock.assert_called_once_with(item.location)


@pytest.mark.django_db
class TestHomeCategorySignal:
  """Adding the 'home' category forces location visibility to 'family'."""

  def test_home_category_sets_visibility_family(self):
    location = LocationFactory(visibility='p')
    home = CategoryFactory(slug='home', status='p')
    location.categories.add(home)
    location.refresh_from_db()
    assert location.visibility == 'f'

  def test_non_home_category_does_not_change_visibility(self):
    location = LocationFactory(visibility='p')
    other = CategoryFactory(slug='camping', status='p')
    location.categories.add(other)
    location.refresh_from_db()
    assert location.visibility == 'p'


@pytest.mark.django_db
class TestSignalsMiscCoverage:
  """Cover remaining signal branches."""

  def test_location_saved_skips_when_completeness_in_update_fields(self):
    """Line 21 — avoid recursion when update_fields contains 'completeness'."""
    location = LocationFactory()
    with patch.object(location, 'calculate_completeness') as mock:
      location_saved(
        sender=None, instance=location, raw=False,
        update_fields=frozenset(['completeness']),
      )
    mock.assert_not_called()

  def test_visit_deleted_recalculates(self):
    """Line 56 — visit_deleted calls _recalculate."""
    from locations.models import Visits
    from locations.signals import visit_deleted
    user = UserFactory()
    user.save()
    location = LocationFactory()
    visit = Visits.objects.create(user=user, location=location, year=2024)
    with patch('locations.signals._recalculate') as mock:
      visit_deleted(sender=None, instance=visit)
    mock.assert_called_once_with(visit.location)

  def test_media_saved_raw_skips(self):
    """Line 66 — media_saved with raw=True skips recalculation."""
    from locations.signals import media_saved
    from locations.tests.factories import MediaFactory
    media = MediaFactory()
    with patch('locations.signals._recalculate') as mock:
      media_saved(sender=None, instance=media, raw=True)
    mock.assert_not_called()

  def test_comment_saved_non_location_content_object_skips(self):
    """Line 85 — comment_saved skips if content_object is not a Location."""
    from locations.signals import comment_saved
    from unittest.mock import MagicMock
    comment = MagicMock()
    comment.content_object = object()  # not a Location
    with patch('locations.signals._recalculate') as mock:
      comment_saved(sender=None, instance=comment, raw=False)
    mock.assert_not_called()

  def test_comment_deleted_recalculates_location(self):
    """Lines 93-95 — comment_deleted calls _recalculate for Location content_object."""
    from locations.signals import comment_deleted
    from locations.tests.factories import CommentFactory
    from locations.models import Location
    from django.contrib.contenttypes.models import ContentType
    location = LocationFactory()
    ct = ContentType.objects.get_for_model(location)
    comment = CommentFactory(content_type=ct, object_id=location.pk, status='p')
    with patch('locations.signals._recalculate') as mock:
      comment_deleted(sender=None, instance=comment)
    mock.assert_called_once_with(location)

  def test_comment_deleted_non_location_skips(self):
    """Line 94 — comment_deleted skips if content_object is not a Location."""
    from locations.signals import comment_deleted
    from unittest.mock import MagicMock
    comment = MagicMock()
    comment.content_object = object()
    with patch('locations.signals._recalculate') as mock:
      comment_deleted(sender=None, instance=comment)
    mock.assert_not_called()

  def test_media_deleted_suppresses_exception_on_cascade(self):
    """Lines 72-75 — media_deleted swallows exception when location is already deleted."""
    from locations.signals import media_deleted
    from unittest.mock import MagicMock, PropertyMock
    media = MagicMock()
    type(media).location = PropertyMock(side_effect=Exception('already deleted'))
    # Should not raise
    media_deleted(sender=None, instance=media)

  def test_listitem_deleted_recalculates(self):
    """Line 111 — listitem_deleted calls _recalculate."""
    from locations.signals import listitem_deleted
    from locations.models import List, ListItem
    user = UserFactory()
    user.save()
    location = LocationFactory()
    lst = List.objects.create(name='Test', user=user, status='p')
    item = ListItem(list=lst, location=location)
    item.save()
    with patch('locations.signals._recalculate') as mock:
      listitem_deleted(sender=None, instance=item)
    mock.assert_called_once_with(item.location)
