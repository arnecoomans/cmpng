import django
from django.conf import settings


def pytest_configure():
    pass  # settings handled by pytest.ini DJANGO_SETTINGS_MODULE