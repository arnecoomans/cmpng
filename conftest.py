import django
from django.conf import settings

import pytest


def pytest_configure():
    pass  # settings handled by pytest.ini DJANGO_SETTINGS_MODULE


@pytest.fixture(autouse=True)
def isolated_media_root(settings, tmp_path):
    """Redirect MEDIA_ROOT to a per-test temp directory so test files never accumulate."""
    settings.MEDIA_ROOT = str(tmp_path / 'media')