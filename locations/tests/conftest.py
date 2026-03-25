import pytest
from django.contrib.auth.models import User
from contextlib import contextmanager
from django.test.utils import CaptureQueriesContext
from django.db import connection

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
    )

@contextmanager
def assert_num_queries(n):
    with CaptureQueriesContext(connection) as ctx:
        yield
    assert len(ctx.captured_queries) == n, (
        f'Expected {n} queries, got {len(ctx.captured_queries)}'
    )