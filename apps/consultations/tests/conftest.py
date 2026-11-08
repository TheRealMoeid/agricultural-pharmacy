import pytest
from django.core.cache import cache

from apps.consultations import notifications


@pytest.fixture(autouse=True)
def fresh_cache():
    """The submission limit lives in the cache; every test starts with nobody counted."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def telegram_off(settings, monkeypatch):
    """No test may talk to Telegram, whatever the developer's own .env says.

    Every posting test saves a request, which asks for a notification. With the
    two values empty the adapter does not even try (the "off" path), and the
    one function that opens a connection is replaced so that a stray call fails
    loudly instead of leaving the machine. Tests that want the other paths set
    the two values again and replace the sender themselves.
    """
    settings.TELEGRAM_BOT_TOKEN = ""
    settings.TELEGRAM_CHAT_ID = ""

    def no_network(*args, **kwargs):
        raise AssertionError("a test tried to reach the Telegram API")

    monkeypatch.setattr(notifications, "post_to_telegram", no_network)
    yield
