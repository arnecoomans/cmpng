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
