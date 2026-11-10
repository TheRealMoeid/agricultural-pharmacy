"""A small per-visitor limit on form submissions (D12, D41).

Written here instead of using django-ratelimit: that package's own system
check refuses Django's in-memory, file and database caches (it wants
memcached or Redis), and this site deliberately has no such service. A
visitor gets SUBMISSION_LIMIT submissions per SUBMISSION_WINDOW seconds, counted
in Django's cache from the first one (a fixed window, not a sliding one).

The cache is per process. With several Gunicorn workers each keeps its own
count, so the real limit is a few times higher than the number here, which is
fine for stopping spam but not a hard guarantee. A restart forgets everyone.

Who is "a visitor": the address in REMOTE_ADDR, or, behind a proxy, the header
named by the CLIENT_IP_HEADER setting. Nginx is set up to overwrite that
header with a single address (`proxy_set_header X-Real-IP $remote_addr;`),
never passing on one the visitor sent. Render's own proxy instead sets
X-Forwarded-For, appending to it rather than replacing it, so that header can
hold a comma-separated chain ("client, proxy1, proxy2"); the first address in
the chain is the visitor's own, and is the one used below (D44).
"""
import ipaddress

from django.conf import settings
from django.core.cache import cache

SUBMISSION_LIMIT = 5
SUBMISSION_WINDOW = 60 * 60  # seconds


def client_ip(request) -> str:
    """The visitor's address. A header value that is not an IP is ignored."""
    header = getattr(settings, "CLIENT_IP_HEADER", "")
    if header:
        value = request.META.get(header, "").split(",")[0].strip()
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            pass
    return request.META.get("REMOTE_ADDR", "")


def over_limit(request) -> bool:
    """Count this submission, and say whether the visitor is past the limit."""
    key = f"consultation-submit:{client_ip(request)}"
    cache.add(key, 0, SUBMISSION_WINDOW)  # starts the window on the first one
    try:
        count = cache.incr(key)
    except ValueError:  # the entry expired between add() and incr()
        cache.set(key, 1, SUBMISSION_WINDOW)
        count = 1
    return count > SUBMISSION_LIMIT
