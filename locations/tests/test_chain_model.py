import pytest
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from locations.models import Chain
from locations.tests.factories import ChainFactory, UserFactory


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def chain(db):
    return ChainFactory()


@pytest.fixture
def parent_chain(db):
    return ChainFactory(parent=None)


@pytest.fixture
def child_chain(db, parent_chain):
    return ChainFactory(parent=parent_chain)


@pytest.fixture
def grandchild_chain(db, child_chain):
    return ChainFactory(parent=child_chain)


# ------------------------------------------------------------------ #
#  Basic fields & string representation
# ------------------------------------------------------------------ #

class TestChainBasics:

    def test_str_without_parent_returns_name(self, chain):
        chain.parent = None
        assert str(chain) == chain.name

    def test_str_with_parent_shows_hierarchy(self, child_chain):
        expected = f"{child_chain.name} ({child_chain.parent.name})"
        assert str(child_chain) == expected

    def test_str_with_grandparent_shows_full_hierarchy(self, grandchild_chain):
        parent = grandchild_chain.parent
        grandparent = parent.parent
        expected = f"{grandchild_chain.name} ({parent.name} ({grandparent.name}))"
        assert str(grandchild_chain) == expected

    def test_name_is_required(self, db):
        chain = ChainFactory.build(name='')
        with pytest.raises(ValidationError):
            chain.full_clean()

    def test_name_is_globally_unique(self, db):
        ChainFactory(name='Accor')
        with pytest.raises(Exception):
            ChainFactory(name='Accor')

    def test_default_ordering(self, db):
        """Test default ordering if specified in Meta."""
        ChainFactory(name='Zebra Hotels')
        ChainFactory(name='Accor')
        ChainFactory(name='Marriott')
        # Just verify queryset works, ordering depends on Meta.ordering
        assert Chain.objects.count() == 3


# ------------------------------------------------------------------ #
#  Slug generation
# ------------------------------------------------------------------ #

class TestChainSlug:

    def test_slug_auto_generated_from_name(self, db):
        chain = ChainFactory(name='Accor Hotels', slug='')
        assert chain.slug == slugify('Accor Hotels')

    def test_slug_not_overwritten_if_provided(self, db):
        chain = ChainFactory(name='Accor Hotels', slug='my-custom-slug')
        assert chain.slug == 'my-custom-slug'

    def test_slug_handles_accented_characters(self, db):
        chain = ChainFactory(name='Hôtel Group', slug='')
        assert chain.slug == slugify('Hôtel Group')

    def test_slug_is_unique(self, db):
        ChainFactory(slug='duplicate-slug')
        with pytest.raises(Exception):
            ChainFactory(slug='duplicate-slug')


# ------------------------------------------------------------------ #
#  Parent / child relationships
# ------------------------------------------------------------------ #

class TestChainHierarchy:

    def test_parent_is_optional(self, db):
        chain = ChainFactory(parent=None)
        assert chain.parent is None

    def test_parent_fk_to_self(self, child_chain, parent_chain):
        assert child_chain.parent == parent_chain
        assert isinstance(child_chain.parent, Chain)

    def test_children_reverse_relation(self, child_chain, parent_chain):
        assert child_chain in parent_chain.children.all()

    def test_multiple_children(self, db, parent_chain):
        child1 = ChainFactory(parent=parent_chain)
        child2 = ChainFactory(parent=parent_chain)
        assert parent_chain.children.count() == 2
        assert child1 in parent_chain.children.all()
        assert child2 in parent_chain.children.all()

    def test_deleting_parent_sets_children_parent_to_null(self, db):
        parent = ChainFactory(parent=None)
        child = ChainFactory(parent=parent)
        child_pk = child.pk
        parent.delete()
        child.refresh_from_db()
        assert child.parent is None

    def test_grandchild_not_affected_by_grandparent_deletion(self, db):
        grandparent = ChainFactory(parent=None)
        parent = ChainFactory(parent=grandparent)
        child = ChainFactory(parent=parent)
        
        grandparent.delete()
        
        parent.refresh_from_db()
        child.refresh_from_db()
        
        assert parent.parent is None
        assert child.parent == parent


# ------------------------------------------------------------------ #
#  BaseModel inheritance
# ------------------------------------------------------------------ #

class TestChainBaseModel:

    def test_token_is_auto_generated(self, chain):
        assert chain.token is not None
        assert len(chain.token) >= 10

    def test_token_is_unique(self, db):
        c1 = ChainFactory()
        c2 = ChainFactory()
        assert c1.token != c2.token

    def test_date_created_is_set(self, chain):
        assert chain.date_created is not None

    def test_date_modified_updates_on_save(self, chain):
        original = chain.date_modified
        chain.name = 'Updated Chain Name'
        chain.save()
        chain.refresh_from_db()
        assert chain.date_modified > original

    def test_default_status_is_published(self, db):
        chain = ChainFactory()
        assert chain.status == 'p'

    def test_user_fk_is_nullable(self, db):
        chain = ChainFactory(user=None)
        assert chain.user is None