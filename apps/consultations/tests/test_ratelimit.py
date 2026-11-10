import pytest
from django.core.cache import cache
from django.test import RequestFactory

from apps.consultations import ratelimit
from apps.consultations.ratelimit import SUBMISSION_LIMIT, SUBMISSION_WINDOW, client_ip, over_limit


def request_from(ip="203.0.113.7", **meta):
    return RequestFactory().post("/consultation/", REMOTE_ADDR=ip, **meta)


# --- who the visitor is -------------------------------------------------------------------


def test_the_visitor_is_the_remote_address_by_default():
    assert client_ip(request_from("203.0.113.7")) == "203.0.113.7"


def test_behind_the_proxy_the_named_header_is_used(settings):
    settings.CLIENT_IP_HEADER = "HTTP_X_REAL_IP"
    assert client_ip(request_from("127.0.0.1", HTTP_X_REAL_IP="198.51.100.9")) == "198.51.100.9"


def test_the_header_is_ignored_when_no_header_is_configured(settings):
    settings.CLIENT_IP_HEADER = ""
    assert client_ip(request_from("127.0.0.1", HTTP_X_REAL_IP="198.51.100.9")) == "127.0.0.1"


@pytest.mark.parametrize("junk", ["", "not an ip", ", 5.6.7.8", "<script>"])
def test_a_header_that_is_not_an_ip_falls_back_to_the_remote_address(settings, junk):
    settings.CLIENT_IP_HEADER = "HTTP_X_REAL_IP"
    assert client_ip(request_from("127.0.0.1", HTTP_X_REAL_IP=junk)) == "127.0.0.1"


def test_a_missing_header_falls_back_to_the_remote_address(settings):
    settings.CLIENT_IP_HEADER = "HTTP_X_REAL_IP"
    assert client_ip(request_from("127.0.0.1")) == "127.0.0.1"


def test_ipv6_addresses_work_too(settings):
    settings.CLIENT_IP_HEADER = "HTTP_X_REAL_IP"
    assert client_ip(request_from("127.0.0.1", HTTP_X_REAL_IP="2001:db8::1")) == "2001:db8::1"


def test_a_forwarded_for_chain_uses_only_the_first_address(settings):
    # Render's proxy (and any other chained proxy) appends to this header
    # rather than replacing it, so it can read "client, proxy1, proxy2" (D44).
    settings.CLIENT_IP_HEADER = "HTTP_X_FORWARDED_FOR"
    assert client_ip(request_from("127.0.0.1", HTTP_X_FORWARDED_FOR="198.51.100.9, 10.0.0.1")) == "198.51.100.9"


def test_a_forwarded_for_chain_still_falls_back_when_the_first_address_is_junk(settings):
    settings.CLIENT_IP_HEADER = "HTTP_X_FORWARDED_FOR"
    assert client_ip(request_from("127.0.0.1", HTTP_X_FORWARDED_FOR="not an ip, 10.0.0.1")) == "127.0.0.1"


# --- the limit ----------------------------------------------------------------------------


def test_the_agreed_numbers():
    assert (SUBMISSION_LIMIT, SUBMISSION_WINDOW) == (5, 3600)


def test_the_first_submissions_up_to_the_limit_are_fine_and_the_next_is_not():
    request = request_from()
    assert [over_limit(request) for _ in range(SUBMISSION_LIMIT + 2)] == [False] * SUBMISSION_LIMIT + [True, True]


def test_each_visitor_has_their_own_count():
    for _ in range(SUBMISSION_LIMIT + 1):
        over_limit(request_from("203.0.113.7"))
    assert over_limit(request_from("203.0.113.8")) is False


def test_the_count_starts_again_after_the_window(monkeypatch):
    clock = [1_000_000.0]
    monkeypatch.setattr("time.time", lambda: clock[0])
    request = request_from()
    for _ in range(SUBMISSION_LIMIT + 1):
        over_limit(request)
    assert over_limit(request) is True
    clock[0] += SUBMISSION_WINDOW + 1
    assert over_limit(request) is False


def test_the_window_is_fixed_from_the_first_submission_not_pushed_back_by_later_ones(monkeypatch):
    clock = [1_000_000.0]
    monkeypatch.setattr("time.time", lambda: clock[0])
    request = request_from()
    over_limit(request)
    clock[0] += SUBMISSION_WINDOW - 10
    for _ in range(SUBMISSION_LIMIT):
        over_limit(request)
    clock[0] += 20  # past the window counted from the first submission
    assert over_limit(request) is False


def test_an_entry_that_expires_between_the_two_cache_calls_is_handled(monkeypatch):
    request = request_from()
    real_incr = cache.incr

    def expired(key, delta=1):
        cache.delete(key)
        return real_incr(key, delta)  # raises ValueError: the key is gone

    monkeypatch.setattr(ratelimit.cache, "incr", expired)
    assert over_limit(request) is False
