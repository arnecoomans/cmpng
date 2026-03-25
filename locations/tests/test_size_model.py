import pytest
from locations.models.Size import Size
from locations.tests.factories import CategoryFactory


@pytest.mark.django_db
class TestSizeStr:

  def test_str_without_categories(self):
    size = Size.objects.create(code='S', name='Small')
    assert str(size) == 'Small'

  def test_str_with_categories(self):
    size = Size.objects.create(code='L', name='Large')
    cat = CategoryFactory(name='Camping')
    size.categories.add(cat)
    assert str(size) == 'Large (Camping)'
