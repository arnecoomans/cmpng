import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import IntegrityError
from django.urls import reverse

from locations.models.Page import Page
from locations.tests.factories import PageFactory, UserFactory


def _url(slug='test-page'):
  return reverse('locations:page_detail', kwargs={'slug': slug})


def force_login(client, user):
  user.save()
  client.force_login(user)


# ------------------------------------------------------------------ #
#  Model
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestPageModel:

  def test_str_includes_title_and_language(self, db):
    page = PageFactory(title='About us', language='en')
    assert 'About us' in str(page)
    assert 'en' in str(page)

  def test_get_absolute_url_contains_slug(self, db):
    page = PageFactory(slug='about')
    assert 'about' in page.get_absolute_url()

  def test_unique_together_slug_language(self, db):
    PageFactory(slug='privacy', language='en')
    with pytest.raises(IntegrityError):
      PageFactory(slug='privacy', language='en')

  def test_same_slug_different_language_allowed(self, db):
    PageFactory(slug='privacy', language='en')
    PageFactory(slug='privacy', language='nl')  # should not raise


# ------------------------------------------------------------------ #
#  View — basic
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestPageDetailView:

  def test_published_page_returns_200(self, client):
    PageFactory(slug='test-page', language='en', status='p')
    response = client.get(_url())
    assert response.status_code == 200

  def test_uses_correct_template(self, client):
    PageFactory(slug='test-page', language='en', status='p')
    response = client.get(_url())
    assert 'pages/page_detail.html' in [t.name for t in response.templates]

  def test_context_contains_page(self, client):
    PageFactory(slug='test-page', language='en', status='p')
    response = client.get(_url())
    assert 'page' in response.context

  def test_nonexistent_slug_returns_404(self, client):
    response = client.get(_url('does-not-exist'))
    assert response.status_code == 404


# ------------------------------------------------------------------ #
#  View — status / staff access
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestPageDetailStatus:

  def test_unpublished_returns_404_for_anonymous(self, client):
    PageFactory(slug='test-page', language='en', status='c')
    response = client.get(_url())
    assert response.status_code == 404

  def test_unpublished_returns_200_for_staff(self, client):
    staff = UserFactory(is_staff=True)
    force_login(client, staff)
    PageFactory(slug='test-page', language='en', status='c')
    response = client.get(_url())
    assert response.status_code == 200

  def test_revoked_returns_404_for_anonymous(self, client):
    PageFactory(slug='test-page', language='en', status='r')
    response = client.get(_url())
    assert response.status_code == 404

  def test_revoked_returns_200_for_staff(self, client):
    staff = UserFactory(is_staff=True)
    force_login(client, staff)
    PageFactory(slug='test-page', language='en', status='r')
    response = client.get(_url())
    assert response.status_code == 200


# ------------------------------------------------------------------ #
#  View — language selection
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestPageDetailLanguage:

  def test_returns_page_matching_active_language(self, client):
    PageFactory(slug='test-page', language='en', title='English page', status='p')
    PageFactory(slug='test-page', language='nl', title='Nederlandse pagina', status='p')
    response = client.get(_url(), HTTP_ACCEPT_LANGUAGE='nl')
    assert response.context['page'].language == 'nl'

  def test_falls_back_to_default_language_when_no_match(self, client):
    default_lang = settings.LANGUAGE_CODE.split('-')[0]
    PageFactory(slug='test-page', language=default_lang, title='Default lang page', status='p')
    response = client.get(_url(), HTTP_ACCEPT_LANGUAGE='fr')
    assert response.status_code == 200
    assert response.context['page'].language == default_lang

  def test_returns_404_when_no_language_matches(self, client):
    # Only a non-default language exists — no fallback possible
    default_lang = settings.LANGUAGE_CODE.split('-')[0]
    non_default = next(code for code, _ in settings.LANGUAGES if code != default_lang)
    PageFactory(slug='test-page', language=non_default, status='p')
    response = client.get(_url(), HTTP_ACCEPT_LANGUAGE=default_lang)
    assert response.status_code == 404

  def test_correct_title_served_per_language(self, client):
    PageFactory(slug='test-page', language='en', title='Privacy Policy', status='p')
    PageFactory(slug='test-page', language='nl', title='Privacybeleid', status='p')
    response = client.get(_url(), HTTP_ACCEPT_LANGUAGE='en')
    assert response.context['page'].title == 'Privacy Policy'


# ------------------------------------------------------------------ #
#  Management command
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCreateDefaultPagesCommand:

  def test_creates_default_pages(self, db):
    call_command('create_default_pages', verbosity=0)
    assert Page.objects.filter(slug='cookie-statement').count() >= 1

  def test_creates_one_row_per_language(self, db):
    call_command('create_default_pages', verbosity=0)
    langs = list(Page.objects.filter(slug='cookie-statement').values_list('language', flat=True))
    assert 'en' in langs
    assert 'nl' in langs
    assert 'fr' in langs

  def test_idempotent_does_not_duplicate(self, db):
    call_command('create_default_pages', verbosity=0)
    call_command('create_default_pages', verbosity=0)
    assert Page.objects.filter(slug='cookie-statement', language='en').count() == 1

  def test_skips_existing_leaves_others_intact(self, db):
    PageFactory(slug='cookie-statement', language='en', title='Custom title')
    call_command('create_default_pages', verbosity=0)
    page = Page.objects.get(slug='cookie-statement', language='en')
    assert page.title == 'Custom title'
