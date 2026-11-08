"""Tests for telling the store about a new request (D3, D42).

Nothing here reaches Telegram. `conftest.py` turns the adapter off for every
test and makes the network call impossible; a test that wants the channel on
sets the two values again and replaces the sender, or `urlopen` inside it.

Look-alike characters are written as escapes with the plain text next to them,
as in the other test files.
"""
import datetime
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

import pytest

from apps.catalog.models import Crop
from apps.consultations import notifications
from apps.consultations.models import ConsultationRequest
from apps.consultations.notifications import (
    DETAIL_MAX_LENGTH,
    NOT_CONFIGURED,
    TIMEOUT,
    NotificationError,
    NotificationOutcome,
    format_message,
    is_configured,
    post_to_telegram,
    send_consultation_notification,
)
from apps.core.models import SiteSettings

pytestmark = pytest.mark.django_db

Kind = ConsultationRequest.Kind
NotificationStatus = ConsultationRequest.NotificationStatus
UTC = datetime.timezone.utc

TOKEN = "123456789:AAHnot-a-real-token"
CHAT_ID = "-1001234567890"
API = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"

# 1 Farvardin 1405 is 21 March 2026; Tehran is UTC+3:30, so noon UTC is 15:30.
WHEN = datetime.datetime(2026, 3, 21, 12, 0, tzinfo=UTC)
STAMP = "1405/01/01 15:30"

NAME = "\u0639\u0644\u06cc \u0631\u0636\u0627\u06cc\u06cc"  # علی رضایی
ASK = "\u0628\u0631\u06af\u0647\u0627\u06cc \u06af\u0646\u062f\u0645 \u0632\u0631\u062f \u0634\u062f\u0647"  # برگهای گندم زرد شده
VILLAGE = "\u0622\u0642\u200c\u0622\u0628\u0627\u062f"  # آق‌آباد
WHEAT = "\u06af\u0646\u062f\u0645"  # گندم
PHONE_TYPED = "09121234567"
PHONE_SHOWN = "0912 123 4567"

# The message's own labels, one constant per line of it.
TITLE = "\U0001f514 \u062f\u0631\u062e\u0648\u0627\u0633\u062a \u062a\u0627\u0632\u0647 \u0627\u0632 \u0633\u0627\u06cc\u062a"  # 🔔 درخواست تازه از سایت
LABEL_KIND = "\u0646\u0648\u0639:"  # نوع:
LABEL_NAME = "\u0646\u0627\u0645:"  # نام:
LABEL_PHONE = "\u062a\u0644\u0641\u0646:"  # تلفن:
LABEL_CROP = "\u06af\u06cc\u0627\u0647:"  # گیاه:
LABEL_ADDRESS = "\u0631\u0648\u0633\u062a\u0627 \u06cc\u0627 \u0646\u0634\u0627\u0646\u06cc:"  # روستا یا نشانی:
LABEL_TEXT = "\u0645\u062a\u0646 \u067e\u06cc\u0627\u0645:"  # متن پیام:
LABEL_TIME = "\u0632\u0645\u0627\u0646:"  # زمان:
FEE_TEXT = "\u0647\u0632\u06cc\u0646\u0647 \u0628\u0627\u0632\u062f\u06cc\u062f"  # هزینه بازدید


def make(**overrides):
    """A stored request with a fixed time, so the expected message is fixed too."""
    base = {"kind": Kind.QUESTION, "name": NAME, "phone": PHONE_TYPED, "message": ASK}
    saved = ConsultationRequest.objects.create(**{**base, **overrides})
    ConsultationRequest.objects.filter(pk=saved.pk).update(created_at=WHEN)
    saved.refresh_from_db()
    return saved


@pytest.fixture
def telegram_on(settings):
    """Both values set: the adapter will try to send."""
    settings.TELEGRAM_BOT_TOKEN = TOKEN
    settings.TELEGRAM_CHAT_ID = CHAT_ID


@pytest.fixture
def telegram(settings, monkeypatch):
    """A configured, faked Telegram: gives back the list of texts that were sent."""
    settings.TELEGRAM_BOT_TOKEN = TOKEN
    settings.TELEGRAM_CHAT_ID = CHAT_ID
    sent = []
    monkeypatch.setattr(notifications, "post_to_telegram", lambda text: sent.append(text))
    return sent


# --- the message the store receives ---------------------------------------------------------


def test_a_question_message_carries_the_kind_the_name_the_phone_the_crop_the_text_and_the_time():
    request = make(crop=Crop.objects.create(name=WHEAT))
    assert format_message(request) == "\n".join(
        [
            TITLE,
            "",
            f"{LABEL_KIND} {Kind.QUESTION.label}",
            f"{LABEL_NAME} {NAME}",
            f"{LABEL_PHONE} {PHONE_SHOWN}",
            f"{LABEL_CROP} {WHEAT}",
            f"{LABEL_TEXT}",
            ASK,
            f"{LABEL_TIME} {STAMP}",
        ]
    )


def test_a_farm_visit_message_shows_the_address_and_its_optional_text():
    request = make(kind=Kind.FARM_VISIT, message=ASK, village_or_address=VILLAGE)
    assert format_message(request) == "\n".join(
        [
            TITLE,
            "",
            f"{LABEL_KIND} {Kind.FARM_VISIT.label}",
            f"{LABEL_NAME} {NAME}",
            f"{LABEL_PHONE} {PHONE_SHOWN}",
            f"{LABEL_ADDRESS} {VILLAGE}",
            f"{LABEL_TEXT}",
            ASK,
            f"{LABEL_TIME} {STAMP}",
        ]
    )


def test_a_farm_visit_without_a_text_has_no_message_line():
    lines = format_message(make(kind=Kind.FARM_VISIT, message="", village_or_address=VILLAGE)).splitlines()
    assert f"{LABEL_ADDRESS} {VILLAGE}" in lines
    assert LABEL_TEXT not in lines


def test_a_question_without_a_crop_has_no_crop_line():
    lines = format_message(make()).splitlines()
    assert not [line for line in lines if line.startswith(LABEL_CROP)]


def test_the_phone_is_written_in_the_readable_iranian_form():
    text = format_message(make())
    assert PHONE_SHOWN in text
    assert PHONE_TYPED not in text


def test_the_time_is_the_jalali_stamp_the_inbox_shows_not_the_utc_one():
    text = format_message(make())
    assert STAMP in text
    assert "12:00" not in text


def test_a_multi_line_text_keeps_its_line_breaks():
    text = format_message(make(message=ASK + "\n\n" + WHEAT))
    assert (ASK + "\n\n" + WHEAT) in text


def test_the_farm_visit_fee_is_never_part_of_the_message():
    site = SiteSettings.load()
    site.show_farm_visit_fee = True
    site.farm_visit_fee_text = FEE_TEXT
    site.save()
    text = format_message(make(kind=Kind.FARM_VISIT, message="", village_or_address=VILLAGE))
    assert FEE_TEXT not in text


# --- sending, with the channel faked ---------------------------------------------------------


def test_a_successful_send_is_reported_as_sent_with_no_reason(telegram):
    request = make()
    assert send_consultation_notification(request) == NotificationOutcome(NotificationStatus.SENT, "")
    assert telegram == [format_message(request)]


def test_a_failed_send_is_reported_as_failed_with_the_reason(settings, monkeypatch):
    settings.TELEGRAM_BOT_TOKEN = TOKEN
    settings.TELEGRAM_CHAT_ID = CHAT_ID

    def refuse(text):
        raise NotificationError("telegram said no")

    monkeypatch.setattr(notifications, "post_to_telegram", refuse)
    assert send_consultation_notification(make()) == NotificationOutcome(
        NotificationStatus.FAILED, "telegram said no"
    )


def test_nothing_is_sent_and_nothing_is_attempted_without_a_token(settings, monkeypatch):
    settings.TELEGRAM_BOT_TOKEN = ""
    settings.TELEGRAM_CHAT_ID = CHAT_ID
    monkeypatch.setattr(notifications, "post_to_telegram", pytest.fail)  # never called
    assert send_consultation_notification(make()) == NotificationOutcome(
        NotificationStatus.NOT_ATTEMPTED, NOT_CONFIGURED
    )


def test_nothing_is_sent_and_nothing_is_attempted_without_a_chat_id(settings, monkeypatch):
    settings.TELEGRAM_BOT_TOKEN = TOKEN
    settings.TELEGRAM_CHAT_ID = ""
    monkeypatch.setattr(notifications, "post_to_telegram", pytest.fail)
    assert send_consultation_notification(make()) == NotificationOutcome(
        NotificationStatus.NOT_ATTEMPTED, NOT_CONFIGURED
    )


@pytest.mark.parametrize("value", ["", " ", "   \t"])
def test_a_blank_value_counts_as_not_set(settings, value):
    settings.TELEGRAM_BOT_TOKEN = value
    settings.TELEGRAM_CHAT_ID = CHAT_ID
    assert is_configured() is False


def test_the_test_suite_itself_starts_with_notifications_off():
    # conftest.py forces this, so a developer's real .env cannot send anything.
    assert is_configured() is False


def test_the_phone_number_reaches_the_store_but_never_the_log(telegram, caplog):
    caplog.set_level(logging.INFO)
    send_consultation_notification(make())
    assert PHONE_SHOWN in telegram[0]  # the store needs it to call back
    assert PHONE_TYPED not in caplog.text
    assert PHONE_SHOWN not in caplog.text


def test_a_failure_is_logged_with_the_request_and_the_reason_but_nothing_else(settings, monkeypatch, caplog):
    settings.TELEGRAM_BOT_TOKEN = TOKEN
    settings.TELEGRAM_CHAT_ID = CHAT_ID

    def refuse(text):
        raise NotificationError("nope")

    monkeypatch.setattr(notifications, "post_to_telegram", refuse)
    request = make()
    with caplog.at_level(logging.WARNING):
        send_consultation_notification(request)
    assert f"request {request.pk}" in caplog.text
    assert "nope" in caplog.text
    assert TOKEN not in caplog.text
    assert PHONE_TYPED not in caplog.text


# --- the call to Telegram itself ----------------------------------------------------------------
#
# These call the imported function directly: conftest.py replaces the module
# attribute, and these tests are the ones allowed to run the real one.


class FakeResponse:
    def __init__(self, body=b'{"ok": true}', status=200):
        self.body = body
        self.status = status
        self.closed = False

    def getcode(self):
        return self.status

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.closed = True
        return False


def fake_urlopen(monkeypatch, body=b'{"ok": true}', status=200, raises=None):
    """Replace the one network call; gives back the list of (request, timeout) it saw."""
    calls = []

    def opener(request, timeout=None):
        calls.append((request, timeout))
        if raises is not None:
            raise raises
        return FakeResponse(body, status)

    monkeypatch.setattr(notifications, "urlopen", opener)
    return calls


def test_the_call_is_a_post_to_the_bot_api_with_the_chat_and_the_text(telegram_on, monkeypatch):
    calls = fake_urlopen(monkeypatch)
    post_to_telegram("hello")
    (request, _timeout), = calls
    assert request.full_url == API
    assert request.get_method() == "POST"
    assert parse_qs(request.data.decode()) == {"chat_id": [CHAT_ID], "text": ["hello"]}


def test_the_timeout_is_a_few_seconds_and_is_passed_on(telegram_on, monkeypatch):
    calls = fake_urlopen(monkeypatch)
    post_to_telegram("hello")
    assert TIMEOUT == 5
    assert calls[0][1] == TIMEOUT


def test_a_good_answer_returns_quietly(telegram_on, monkeypatch):
    fake_urlopen(monkeypatch, body=json.dumps({"ok": True, "result": {}}).encode())
    assert post_to_telegram("hello") is None


def test_an_answer_that_says_not_ok_raises_with_telegrams_own_words(telegram_on, monkeypatch):
    body = json.dumps({"ok": False, "description": "Bad Request: chat not found"}).encode()
    fake_urlopen(monkeypatch, body=body)
    with pytest.raises(NotificationError) as exc:
        post_to_telegram("hello")
    assert "chat not found" in str(exc.value)


@pytest.mark.parametrize("body", [b"", b"{}", b'{"ok": false}'])
def test_an_empty_or_unspecific_answer_is_a_refusal_too(telegram_on, monkeypatch, body):
    fake_urlopen(monkeypatch, body=body)
    with pytest.raises(NotificationError):
        post_to_telegram("hello")


def test_an_http_error_raises_with_the_status(telegram_on, monkeypatch):
    error = HTTPError(API, 401, "Unauthorized", hdrs=None, fp=None)
    fake_urlopen(monkeypatch, raises=error)
    with pytest.raises(NotificationError) as exc:
        post_to_telegram("hello")
    assert "401" in str(exc.value)


def test_an_answer_that_is_not_200_raises_with_the_status(telegram_on, monkeypatch):
    fake_urlopen(monkeypatch, body=b"", status=502)
    with pytest.raises(NotificationError) as exc:
        post_to_telegram("hello")
    assert "502" in str(exc.value)


def test_a_timeout_raises_the_short_reason(telegram_on, monkeypatch):
    fake_urlopen(monkeypatch, raises=TimeoutError("timed out"))
    with pytest.raises(NotificationError) as exc:
        post_to_telegram("hello")
    assert str(exc.value) == notifications.UNREACHABLE


def test_a_connection_error_raises_the_short_reason(telegram_on, monkeypatch):
    fake_urlopen(monkeypatch, raises=URLError(ConnectionRefusedError(10061, "refused")))
    with pytest.raises(NotificationError) as exc:
        post_to_telegram("hello")
    assert str(exc.value) == notifications.UNREACHABLE


def test_an_answer_that_is_not_json_raises_the_short_reason(telegram_on, monkeypatch):
    fake_urlopen(monkeypatch, body=b"<html>oops</html>")
    with pytest.raises(NotificationError) as exc:
        post_to_telegram("hello")
    assert str(exc.value) == notifications.UNREADABLE


def test_telegrams_explanation_is_cut_to_a_reason(telegram_on, monkeypatch):
    body = json.dumps({"ok": False, "description": "x" * 500}).encode()
    fake_urlopen(monkeypatch, body=body)
    with pytest.raises(NotificationError) as exc:
        post_to_telegram("hello")
    assert len(str(exc.value)) == DETAIL_MAX_LENGTH
    assert str(exc.value).endswith("\u2026")  # …


@pytest.mark.parametrize(
    "failure",
    [
        HTTPError(API, 401, "Unauthorized", hdrs=None, fp=None),
        URLError(ConnectionRefusedError(10061, "refused")),
        TimeoutError("timed out"),
    ],
)
def test_no_reason_ever_carries_the_token(telegram_on, monkeypatch, caplog, failure):
    fake_urlopen(monkeypatch, raises=failure)
    # Back to the real sender: conftest.py replaces it for every test.
    monkeypatch.setattr(notifications, "post_to_telegram", post_to_telegram)
    with caplog.at_level(logging.WARNING):
        outcome = send_consultation_notification(make())
    assert outcome.status == NotificationStatus.FAILED
    assert TOKEN not in outcome.detail
    assert TOKEN not in caplog.text
