import pytest
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from locations.models import Category
from locations.tests.factories import CategoryFactory, UserFactory


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def category(db):
    return CategoryFactory()


@pytest.fixture
def parent_category(db):
    return CategoryFactory(parent=None)


@pytest.fixture
def child_category(db, parent_category):
    return CategoryFactory(parent=parent_category)


# ------------------------------------------------------------------ #
#  Basic field & string representation
# ------------------------------------------------------------------ #

class TestCategoryBasics:

    def test_str_without_parent_returns_name(self, category):
        category.parent = None
        assert str(category) == category.name

    def test_str_with_parent_returns_parent_and_name(self, child_category):
        assert str(child_category) == f"{child_category.parent.name}: {child_category.name}"

    def test_name_is_required(self, db):
        category = CategoryFactory.build(name='')
        with pytest.raises(ValidationError):
            category.full_clean()

    def test_name_is_unique(self, db):
        CategoryFactory(name='Food')
        with pytest.raises(Exception):
            CategoryFactory(name='Food')

    def test_default_ordering_is_by_name(self, db):
        CategoryFactory(name='Zebra')
        CategoryFactory(name='Apple')
        CategoryFactory(name='Mango')
        names = list(Category.objects.values_list('name', flat=True))
        assert names == sorted(names)


# ------------------------------------------------------------------ #
#  Slug generation
# ------------------------------------------------------------------ #

class TestCategorySlug:

    def test_slug_auto_generated_from_name(self, db):
        category = CategoryFactory(name='Food & Drink', slug='')
        assert category.slug == slugify('Food & Drink')

    def test_slug_not_overwritten_if_provided(self, db):
        category = CategoryFactory(name='Food & Drink', slug='my-custom-slug')
        assert category.slug == 'my-custom-slug'

    def test_slug_handles_accented_characters(self, db):
        category = CategoryFactory(name='Café Culture', slug='')
        assert category.slug == slugify('Café Culture')

    def test_slug_is_unique(self, db):
        CategoryFactory(slug='duplicate-slug')
        with pytest.raises(Exception):
            CategoryFactory(slug='duplicate-slug')


# ------------------------------------------------------------------ #
#  Parent / child relationships
# ------------------------------------------------------------------ #

class TestCategoryHierarchy:

    def test_parent_is_optional(self, db):
        category = CategoryFactory(parent=None)
        assert category.parent is None

    def test_parent_fk_to_self(self, child_category, parent_category):
        assert child_category.parent == parent_category
        assert isinstance(child_category.parent, Category)

    def test_children_reverse_relation(self, child_category, parent_category):
        assert child_category in parent_category.children.all()

    def test_multiple_children(self, db, parent_category):
        child1 = CategoryFactory(parent=parent_category)
        child2 = CategoryFactory(parent=parent_category)
        assert parent_category.children.count() == 2
        assert child1 in parent_category.children.all()
        assert child2 in parent_category.children.all()

    def test_cascade_delete_removes_children(self, db):
        parent = CategoryFactory(parent=None)
        child = CategoryFactory(parent=parent)
        grandchild = CategoryFactory(parent=child)
        parent.delete()
        assert not Category.objects.filter(pk=child.pk).exists()
        assert not Category.objects.filter(pk=grandchild.pk).exists()


# ------------------------------------------------------------------ #
#  BaseModel inheritance
# ------------------------------------------------------------------ #

class TestCategoryBaseModel:

    def test_token_is_auto_generated(self, category):
        assert category.token is not None
        assert len(category.token) >= 10

    def test_token_is_unique(self, db):
        c1 = CategoryFactory()
        c2 = CategoryFactory()
        assert c1.token != c2.token

    def test_date_created_is_set(self, category):
        assert category.date_created is not None

    def test_date_modified_updates_on_save(self, category):
        original = category.date_modified
        category.name = 'Updated Name'
        category.save()
        category.refresh_from_db()
        assert category.date_modified > original

    def test_default_status_is_published(self, db):
        category = CategoryFactory()
        assert category.status == 'p'

    def test_user_fk_is_nullable(self, db):
        category = CategoryFactory(user=None)
        assert category.user is None

    def test_get_absolute_url_contains_slug(self, db):
        cat = CategoryFactory(slug='glamping')
        assert 'glamping' in cat.get_absolute_url()