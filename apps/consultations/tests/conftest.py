import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def fresh_cache():
    """The submission limit lives in the cache; every test starts with nobody counted."""
    cache.clear()
    yield
    cache.clear()
