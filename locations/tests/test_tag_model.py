import pytest
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from locations.models import Tag
from locations.tests.factories import TagFactory, UserFactory, LocationFactory, CategoryFactory


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def tag(db):
    return TagFactory()


@pytest.fixture
def parent_tag(db):
    return TagFactory(parent=None)


@pytest.fixture
def child_tag(db, parent_tag):
    return TagFactory(parent=parent_tag)


# ------------------------------------------------------------------ #
#  Basic field & string representation
# ------------------------------------------------------------------ #

class TestTagBasics:

    def test_str_returns_display_name(self, tag):
        tag.parent = None
        assert str(tag) == tag.name

    def test_display_name_with_parent(self, child_tag):
        expected = f"{child_tag.parent.name}: {child_tag.name}"
        assert child_tag.display_name() == expected

    def test_display_name_without_parent(self, tag):
        tag.parent = None
        assert tag.display_name() == tag.name

    def test_name_is_required(self, db):
        # Both name and slug empty should fail
        tag = TagFactory.build(name='', slug='')
        with pytest.raises(ValidationError):
            tag.full_clean()

    def test_default_ordering_is_by_name(self, db):
        TagFactory(name='Zebra')
        TagFactory(name='Apple')
        TagFactory(name='Mango')
        names = list(Tag.objects.values_list('name', flat=True))
        assert names == sorted(names)


# ------------------------------------------------------------------ #
#  Slug generation (bidirectional)
# ------------------------------------------------------------------ #

class TestTagSlug:

    def test_slug_auto_generated_from_name(self, db):
        tag = TagFactory(name='Family Friendly', slug='')
        assert tag.slug == slugify('Family Friendly')

    def test_name_auto_generated_from_slug(self, db):
        tag = TagFactory(name='', slug='pet-friendly')
        assert tag.name == 'Pet Friendly'

    def test_slug_not_overwritten_if_both_provided(self, db):
        tag = TagFactory(name='Custom Name', slug='custom-slug')
        assert tag.slug == 'custom-slug'
        assert tag.name == 'Custom Name'

    def test_slug_handles_accented_characters(self, db):
        tag = TagFactory(name='Café Culture', slug='')
        assert tag.slug == slugify('Café Culture')

    def test_slug_is_unique(self, db):
        TagFactory(slug='duplicate-slug')
        with pytest.raises(Exception):
            TagFactory(slug='duplicate-slug')


# ------------------------------------------------------------------ #
#  Uniqueness validation
# ------------------------------------------------------------------ #

class TestTagUniqueness:

    def test_same_name_allowed_under_different_parents(self, db):
        parent1 = TagFactory(parent=None)
        parent2 = TagFactory(parent=None)
        TagFactory(name='Popular', parent=parent1)
        TagFactory(name='Popular', parent=parent2)  # should not raise

    def test_duplicate_name_under_same_parent_raises(self, db):
        parent = TagFactory(parent=None)
        TagFactory(name='Popular', parent=parent)
        duplicate = TagFactory.build(name='Popular', parent=parent)
        with pytest.raises(ValidationError):
            duplicate.full_clean()

    def test_different_root_tag_names_allowed(self, db):
        TagFactory(name='Outdoor', parent=None)
        TagFactory(name='Indoor', parent=None)  # should not raise

    def test_duplicate_root_tag_name_raises(self, db):
        TagFactory(name='Popular', parent=None)
        duplicate = TagFactory.build(name='Popular', parent=None)
        with pytest.raises(ValidationError):
            duplicate.full_clean()


# ------------------------------------------------------------------ #
#  Parent / child relationships
# ------------------------------------------------------------------ #

class TestTagHierarchy:

    def test_parent_is_optional(self, db):
        tag = TagFactory(parent=None)
        assert tag.parent is None

    def test_parent_fk_to_self(self, child_tag, parent_tag):
        assert child_tag.parent == parent_tag
        assert isinstance(child_tag.parent, Tag)

    def test_children_reverse_relation(self, child_tag, parent_tag):
        assert child_tag in parent_tag.children.all()

    def test_multiple_children(self, db, parent_tag):
        child1 = TagFactory(parent=parent_tag)
        child2 = TagFactory(parent=parent_tag)
        assert parent_tag.children.count() == 2
        assert child1 in parent_tag.children.all()
        assert child2 in parent_tag.children.all()

    def test_cascade_delete_removes_children(self, db):
        parent = TagFactory(parent=None)
        child = TagFactory(parent=parent)
        grandchild = TagFactory(parent=child)
        parent.delete()
        assert not Tag.objects.filter(pk=child.pk).exists()
        assert not Tag.objects.filter(pk=grandchild.pk).exists()


# ------------------------------------------------------------------ #
#  Location M2M and helper methods
# ------------------------------------------------------------------ #

class TestTagLocationRelations:

    def test_locations_m2m_exists(self, db):
        tag = TagFactory()
        location = LocationFactory()
        location.tags.add(tag)
        assert location in tag.locations.all()

    def test_accommodations_filters_correctly(self, db):
        tag = TagFactory()
        
        # Create categories
        activity_cat = CategoryFactory(name='Activity', parent=None)
        hotel_cat = CategoryFactory(name='Hotels', parent=None)
        
        # Create locations with proper categories
        accommodation = LocationFactory()
        accommodation.categories.add(hotel_cat)
        accommodation._update_types()
        accommodation.save()
        
        activity = LocationFactory()
        activity.categories.add(activity_cat)
        activity._update_types()
        activity.save()
        
        accommodation.tags.add(tag)
        activity.tags.add(tag)
        
        accommodations = tag.accommodations()
        assert accommodation in accommodations
        assert activity not in accommodations

    def test_activities_filters_correctly(self, db):
        tag = TagFactory()
        
        # Create categories
        activity_cat = CategoryFactory(name='Activity', parent=None)
        hotel_cat = CategoryFactory(name='Hotels', parent=None)
        
        # Create locations with proper categories
        accommodation = LocationFactory()
        accommodation.categories.add(hotel_cat)
        accommodation._update_types()
        accommodation.save()
        
        activity = LocationFactory()
        activity.categories.add(activity_cat)
        activity._update_types()
        activity.save()
        
        accommodation.tags.add(tag)
        activity.tags.add(tag)
        
        activities = tag.activities()
        assert activity in activities
        assert accommodation not in activities

    def test_both_types_appear_in_both_methods(self, db):
        tag = TagFactory()
        
        # Create both types of categories
        activity_cat = CategoryFactory(name='Activity', parent=None)
        hotel_cat = CategoryFactory(name='Hotels', parent=None)
        
        # Create location with both categories
        both = LocationFactory()
        both.categories.add(activity_cat, hotel_cat)
        both._update_types()
        both.save()
        
        both.tags.add(tag)
        
        assert both in tag.accommodations()
        assert both in tag.activities()


# ------------------------------------------------------------------ #
#  BaseModel inheritance
# ------------------------------------------------------------------ #

class TestTagBaseModel:

    def test_token_is_auto_generated(self, tag):
        assert tag.token is not None
        assert len(tag.token) >= 10

    def test_token_is_unique(self, db):
        t1 = TagFactory()
        t2 = TagFactory()
        assert t1.token != t2.token

    def test_date_created_is_set(self, tag):
        assert tag.date_created is not None

    def test_date_modified_updates_on_save(self, tag):
        original = tag.date_modified
        tag.name = 'Updated Name'
        tag.save()
        tag.refresh_from_db()
        assert tag.date_modified > original

    def test_default_status_is_published(self, db):
        tag = TagFactory()
        assert tag.status == 'p'

    def test_user_fk_is_nullable(self, db):
        tag = TagFactory(user=None)
        assert tag.user is None


# ------------------------------------------------------------------ #
#  VisibilityModel inheritance
# ------------------------------------------------------------------ #

class TestTagVisibility:

    def test_default_visibility_is_community(self):
        field = Tag._meta.get_field('visibility')
        assert field.default == 'p'

    def test_visibility_can_be_set_to_public(self, db):
        tag = TagFactory(visibility='p')
        assert tag.visibility == 'p'

    def test_visibility_can_be_set_to_private(self, db):
        tag = TagFactory(visibility='q')
        assert tag.visibility == 'q'


# ------------------------------------------------------------------ #
#  Description field
# ------------------------------------------------------------------ #

class TestTagDescription:

    def test_description_is_optional(self, db):
        tag = TagFactory(description='')
        assert tag.description == ''

    def test_description_can_be_set(self, db):
        desc = 'This tag indicates pet-friendly locations'
        tag = TagFactory(description=desc)
        assert tag.description == desc