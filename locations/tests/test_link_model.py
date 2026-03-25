import pytest
from django.core.exceptions import ValidationError

from locations.models import Link
from locations.tests.factories import LinkFactory, LocationFactory


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def link(db):
    return LinkFactory()


@pytest.fixture
def location(db):
    return LocationFactory()


# ------------------------------------------------------------------ #
#  Basic fields & string representation
# ------------------------------------------------------------------ #

class TestLinkBasics:

    def test_str_returns_label_if_provided(self, db):
        link = LinkFactory(label='Official Website')
        assert str(link) == 'Official Website'

    def test_str_returns_display_name_if_no_label(self, db):
        link = LinkFactory(url='https://example.com', label='')
        assert str(link) == 'example.com'

    def test_url_is_required(self, db):
        link = LinkFactory.build(url='')
        with pytest.raises(ValidationError):
            link.save()

    def test_label_is_optional(self, db):
        link = LinkFactory(label='')
        assert link.label == ''


# ------------------------------------------------------------------ #
#  URL validation and normalization
# ------------------------------------------------------------------ #

class TestLinkURLValidation:

    def test_valid_https_url_accepted(self, db):
        link = LinkFactory(url='https://example.com')
        assert link.url == 'https://example.com'

    def test_valid_http_url_accepted(self, db):
        link = LinkFactory(url='http://example.com')
        assert link.url == 'http://example.com'

    def test_url_without_protocol_gets_https(self, db):
        link = LinkFactory(url='example.com')
        assert link.url == 'https://example.com'

    def test_url_with_path_without_protocol_gets_https(self, db):
        link = LinkFactory(url='example.com/page')
        assert link.url == 'https://example.com/page'

    def test_invalid_url_raises_validation_error(self, db):
        link = LinkFactory.build(url='not a url')
        with pytest.raises(ValidationError) as exc_info:
            link.save()
        assert 'url' in exc_info.value.message_dict

    def test_url_with_query_params_accepted(self, db):
        link = LinkFactory(url='https://example.com?param=value')
        assert link.url == 'https://example.com?param=value'

    def test_url_with_fragment_accepted(self, db):
        link = LinkFactory(url='https://example.com#section')
        assert link.url == 'https://example.com#section'


# ------------------------------------------------------------------ #
#  Display name extraction
# ------------------------------------------------------------------ #

class TestLinkDisplayName:

    def test_display_name_extracts_domain(self, db):
        link = LinkFactory(url='https://example.com/some/path', label='')
        assert link.display_name() == 'example.com'

    def test_display_name_removes_www_prefix(self, db):
        link = LinkFactory(url='https://www.example.com', label='')
        assert link.display_name() == 'example.com'

    def test_display_name_with_subdomain(self, db):
        link = LinkFactory(url='https://blog.example.com', label='')
        assert link.display_name() == 'blog.example.com'

    def test_display_name_handles_port(self, db):
        link = LinkFactory(url='https://example.com:8080', label='')
        assert link.display_name() == 'example.com:8080'

    def test_display_name_fallback_on_invalid_url(self, db):
        link = LinkFactory.build(url='invalid', label='')
        # Don't save, just test the method
        assert link.display_name() == 'invalid'


# ------------------------------------------------------------------ #
#  Location relationship
# ------------------------------------------------------------------ #

class TestLinkLocationRelationship:

    def test_link_belongs_to_location(self, link, location):
        link.location = location
        link.save()
        assert link.location == location

    def test_location_reverse_relation(self, db, location):
        link1 = LinkFactory(location=location)
        link2 = LinkFactory(location=location)
        assert link1 in location.links.all()
        assert link2 in location.links.all()
        assert location.links.count() == 2

    def test_deleting_location_cascades_to_links(self, db):
        location = LocationFactory()
        link = LinkFactory(location=location)
        link_pk = link.pk
        location.delete()
        assert not Link.objects.filter(pk=link_pk).exists()


# ------------------------------------------------------------------ #
#  BaseModel inheritance
# ------------------------------------------------------------------ #

class TestLinkBaseModel:

    def test_token_is_auto_generated(self, link):
        assert link.token is not None
        assert len(link.token) >= 10

    def test_date_created_is_set(self, link):
        assert link.date_created is not None

    def test_date_modified_updates_on_save(self, link):
        original = link.date_modified
        link.label = 'Updated Label'
        link.save()
        link.refresh_from_db()
        assert link.date_modified > original

    def test_default_status_is_published(self, db):
        link = LinkFactory()
        assert link.status == 'p'