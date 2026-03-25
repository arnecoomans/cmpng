import pytest
from unittest.mock import patch
from django.test import override_settings

from locations.checks import check_cmnsd_config


def run_checks(**overrides):
  """Run check_cmnsd_config with the test settings, optionally overriding values."""
  with override_settings(**overrides):
    return check_cmnsd_config(app_configs=None)


def warning_ids(warnings):
  return [w.id for w in warnings]


# ------------------------------------------------------------------ #
#  W001 — Required settings
# ------------------------------------------------------------------ #

class TestRequiredSettings:

  def test_no_warnings_when_all_present(self):
    warnings = run_checks(
      GOOGLE_API_KEY='key',
      DEPARTURE_CENTER='Somewhere',
      NEARBY_RANGE=50,
      GUEST_NEARBY_RANGE=10,
    )
    assert 'cmpng.locations.W001' not in warning_ids(warnings)

  def test_warns_for_missing_google_api_key(self):
    with override_settings():
      from django.conf import settings
      original = getattr(settings, 'GOOGLE_API_KEY', None)
      try:
        if hasattr(settings, 'GOOGLE_API_KEY'):
          delattr(settings, 'GOOGLE_API_KEY')
        warnings = check_cmnsd_config(app_configs=None)
        assert 'cmpng.locations.W001' in warning_ids(warnings)
      finally:
        if original is not None:
          settings.GOOGLE_API_KEY = original


# ------------------------------------------------------------------ #
#  W002 — LOGIN_URL
# ------------------------------------------------------------------ #

class TestLoginUrl:

  def test_no_warning_when_login_url_set(self):
    warnings = run_checks(LOGIN_URL='/accounts/login/')
    assert 'cmpng.locations.W002' not in warning_ids(warnings)

  def test_warns_when_login_url_missing(self):
    with override_settings():
      from django.conf import settings
      original = getattr(settings, 'LOGIN_URL', None)
      try:
        if hasattr(settings, 'LOGIN_URL'):
          delattr(settings, 'LOGIN_URL')
        warnings = check_cmnsd_config(app_configs=None)
        assert 'cmpng.locations.W002' in warning_ids(warnings)
      finally:
        if original is not None:
          settings.LOGIN_URL = original


# ------------------------------------------------------------------ #
#  W003 — USE_I18N
# ------------------------------------------------------------------ #

class TestUseI18n:

  def test_no_warning_when_enabled(self):
    warnings = run_checks(USE_I18N=True)
    assert 'cmpng.locations.W003' not in warning_ids(warnings)

  def test_warns_when_disabled(self):
    warnings = run_checks(USE_I18N=False)
    assert 'cmpng.locations.W003' in warning_ids(warnings)


# ------------------------------------------------------------------ #
#  W004 — App ordering
# ------------------------------------------------------------------ #

class TestAppOrdering:

  def test_no_warning_when_local_apps_before_admin(self):
    warnings = run_checks(INSTALLED_APPS=[
      'cmnsd', 'locations', 'django.contrib.admin',
    ])
    assert 'cmpng.locations.W004' not in warning_ids(warnings)

  def test_warns_when_locations_after_admin(self):
    warnings = run_checks(INSTALLED_APPS=[
      'django.contrib.admin', 'locations',
    ])
    assert 'cmpng.locations.W004' in warning_ids(warnings)

  def test_warns_when_cmnsd_after_admin(self):
    warnings = run_checks(INSTALLED_APPS=[
      'django.contrib.admin', 'cmnsd',
    ])
    assert 'cmpng.locations.W004' in warning_ids(warnings)

  def test_no_warning_when_admin_not_installed(self):
    warnings = run_checks(INSTALLED_APPS=['cmnsd', 'locations'])
    assert 'cmpng.locations.W004' not in warning_ids(warnings)


# ------------------------------------------------------------------ #
#  W005 — Middleware order
# ------------------------------------------------------------------ #

class TestMiddlewareOrder:

  def test_no_warning_when_order_correct(self):
    warnings = run_checks(MIDDLEWARE=[
      'django.contrib.sessions.middleware.SessionMiddleware',
      'django.contrib.auth.middleware.AuthenticationMiddleware',
      'django.contrib.messages.middleware.MessageMiddleware',
    ])
    assert 'cmpng.locations.W005' not in warning_ids(warnings)

  def test_warns_when_session_after_auth(self):
    warnings = run_checks(MIDDLEWARE=[
      'django.contrib.auth.middleware.AuthenticationMiddleware',
      'django.contrib.sessions.middleware.SessionMiddleware',
      'django.contrib.messages.middleware.MessageMiddleware',
    ])
    assert 'cmpng.locations.W005' in warning_ids(warnings)

  def test_warns_when_auth_after_messages(self):
    warnings = run_checks(MIDDLEWARE=[
      'django.contrib.sessions.middleware.SessionMiddleware',
      'django.contrib.messages.middleware.MessageMiddleware',
      'django.contrib.auth.middleware.AuthenticationMiddleware',
    ])
    assert 'cmpng.locations.W005' in warning_ids(warnings)


# ------------------------------------------------------------------ #
#  W006 — Template builtins
# ------------------------------------------------------------------ #

class TestTemplateBuiltins:

  _required = [
    'django.templatetags.i18n',
    'cmnsd.templatetags.cmnsd',
    'cmnsd.templatetags.query_filters',
    'locations.templatetags.maps_tags',
    'locations.templatetags.distance_tags',
  ]

  def test_no_warning_when_all_builtins_present(self):
    warnings = run_checks(TEMPLATES=[{
      'BACKEND': 'django.template.backends.django.DjangoTemplates',
      'OPTIONS': {'builtins': self._required, 'context_processors': []},
    }])
    assert 'cmpng.locations.W006' not in warning_ids(warnings)

  def test_warns_for_missing_builtin(self):
    warnings = run_checks(TEMPLATES=[{
      'BACKEND': 'django.template.backends.django.DjangoTemplates',
      'OPTIONS': {'builtins': [], 'context_processors': []},
    }])
    w006 = [w for w in warnings if w.id == 'cmpng.locations.W006']
    assert len(w006) == len(self._required)


# ------------------------------------------------------------------ #
#  W007 — Context processors
# ------------------------------------------------------------------ #

class TestContextProcessors:

  _required = [
    'django.template.context_processors.request',
    'django.contrib.messages.context_processors.messages',
  ]

  def test_no_warning_when_all_processors_present(self):
    warnings = run_checks(TEMPLATES=[{
      'BACKEND': 'django.template.backends.django.DjangoTemplates',
      'OPTIONS': {'context_processors': self._required, 'builtins': []},
    }])
    assert 'cmpng.locations.W007' not in warning_ids(warnings)

  def test_warns_for_missing_processor(self):
    warnings = run_checks(TEMPLATES=[{
      'BACKEND': 'django.template.backends.django.DjangoTemplates',
      'OPTIONS': {'context_processors': [], 'builtins': []},
    }])
    w007 = [w for w in warnings if w.id == 'cmpng.locations.W007']
    assert len(w007) == len(self._required)
