"""Tests for the public consultation pages (D41) and their notification (D42)."""
import re

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.catalog.models import Crop
from apps.consultations import notifications, views
from apps.consultations.models import ConsultationRequest
from apps.consultations.notifications import CRASHED, NOT_CONFIGURED
from apps.consultations.ratelimit import SUBMISSION_LIMIT

pytestmark = pytest.mark.django_db

Kind = ConsultationRequest.Kind
NotificationStatus = ConsultationRequest.NotificationStatus
URL = "/consultation/"
THANKS = "/consultation/thank-you/"
TEL = 'href="tel:+989112747628"'
NAME = "\u0639\u0644\u06cc \u0631\u0636\u0627\u06cc\u06cc"
ASK = "\u0628\u0631\u06af\u0647\u0627\u06cc \u06af\u0646\u062f\u0645 \u0632\u0631\u062f \u0634\u062f\u0647"
VILLAGE = "\u0622\u0642\u200c\u0622\u0628\u0627\u062f"
RECEIVED = "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0634\u0645\u0627 \u062f\u0631\u06cc\u0627\u0641\u062a \u0634\u062f"  # درخواست شما دریافت شد
LIMITED = "\u062f\u0631\u062e\u0648\u0627\u0633\u062a\u200c\u0647\u0627\u06cc \u0632\u06cc\u0627\u062f\u06cc"  # درخواست‌های زیادی


def question(**overrides):
    return {"name": NAME, "phone": "09121234567", "message": ASK, **overrides}


def visit(**overrides):
    return {"name": NAME, "phone": "09121234567", "village_or_address": VILLAGE, **overrides}


def tabs(html):
    nav = re.search(r"<nav[^>]*>(.*?)</nav>", html, re.S).group(1)
    return [(name, 'aria-current="true"' in attrs) for attrs, name in re.findall(r"<a href=\"[^\"]*\"([^>]*)>(.*?)</a>", nav, re.S)]


# --- addresses ---------------------------------------------------------------------------------------


def test_the_addresses():
    assert reverse("consultations:form") == URL
    assert reverse("consultations:thank_you") == THANKS


# --- the form page -----------------------------------------------------------------------------------


def test_the_form_opens_on_the_question_form_by_default(client):
    html = client.get(URL).content.decode()
    assert 'name="message"' in html
    assert 'name="village_or_address"' not in html
    assert tabs(html) == [("\u067e\u0631\u0633\u0634 \u0627\u0632 \u06a9\u0627\u0631\u0634\u0646\u0627\u0633", True), ("\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0628\u0627\u0632\u062f\u06cc\u062f \u0627\u0632 \u0645\u0632\u0631\u0639\u0647", False)]


def test_kind_farm_visit_shows_the_farm_visit_form(client):
    html = client.get(URL, {"kind": "farm_visit"}).content.decode()
    assert 'name="village_or_address"' in html
    assert [current for _, current in tabs(html)] == [False, True]
    assert "\u06af\u0646\u0628\u062f\u06a9\u0627\u0648\u0648\u0633" in html  # the county limit is stated
    assert "\u0628\u0639\u062f \u0627\u0632 \u062a\u0645\u0627\u0633 \u06a9\u0627\u0631\u0634\u0646\u0627\u0633 \u0627\u0639\u0644\u0627\u0645" in html  # the fee is quoted after the call


def test_an_unknown_kind_falls_back_to_the_question_form(client):
    html = client.get(URL, {"kind": "something-else"}).content.decode()
    assert 'name="message"' in html and 'name="village_or_address"' not in html


def test_the_form_posts_back_to_its_own_kind(client):
    html = client.get(URL, {"kind": "farm_visit"}).content.decode()
    assert f'action="{URL}?kind=farm_visit"' in html


def test_the_form_has_a_csrf_token_and_a_hidden_honeypot(client):
    html = client.get(URL).content.decode()
    assert 'name="csrfmiddlewaretoken"' in html
    pot = re.search(r'<div class="([^"]*)" aria-hidden="true"><label>[^<]*<input[^>]*name="website"[^>]*>', html)
    assert pot and "hidden" in pot.group(1).split()
    assert 'tabindex="-1"' in pot.group(0)


def test_optional_fields_are_marked_and_required_ones_are_not(client):
    html = client.get(URL).content.decode()
    label = lambda for_: re.search(rf'<label for="id_{for_}"[^>]*>(.*?)</label>', html, re.S).group(1)
    assert "\u0627\u062e\u062a\u06cc\u0627\u0631\u06cc" in label("crop")  # اختیاری
    for required in ("name", "phone", "message"):
        assert "\u0627\u062e\u062a\u06cc\u0627\u0631\u06cc" not in label(required)


def test_the_crops_are_offered_in_the_select(client):
    wheat = Crop.objects.create(name="\u06af\u0646\u062f\u0645")
    html = client.get(URL).content.decode()
    assert f'<option value="{wheat.pk}">{wheat.name}</option>' in html


def test_the_page_is_persian_rtl_with_the_call_bar_and_nothing_from_other_sites(client):
    html = client.get(URL).content.decode()
    assert '<html lang="fa" dir="rtl"' in html
    assert 'id="call-bar"' in html and html.count(TEL) == 3
    assert not re.search(r'(?:src|href|action)=["\']?(?:https?:)?//', html)
    assert not re.search(r"font-(thin|extralight|light|medium|semibold|extrabold|black)", html)


def test_the_form_page_costs_a_fixed_number_of_queries(client):
    Crop.objects.create(name="\u06af\u0646\u062f\u0645")
    client.get(URL)  # the settings row is created on the first request
    with CaptureQueriesContext(connection) as queries:
        client.get(URL)
    assert len(queries) == 2  # the crops for the select, and the site settings


def test_the_header_and_the_product_page_link_to_the_form(client):
    assert f'href="{URL}"' in client.get("/").content.decode()


# --- sending -----------------------------------------------------------------------------------------


def test_a_valid_question_is_stored_and_the_visitor_is_sent_to_the_thank_you_page(client):
    response = client.post(URL, question())
    assert response.status_code == 302 and response.url == THANKS
    saved = ConsultationRequest.objects.get()
    assert (saved.kind, saved.name, saved.phone, saved.message) == (Kind.QUESTION, NAME, "09121234567", ASK)


def test_a_valid_farm_visit_is_stored_with_the_kind_from_the_address(client):
    response = client.post(URL + "?kind=farm_visit", visit(crop=Crop.objects.create(name="\u06af\u0646\u062f\u0645").pk))
    assert response.status_code == 302
    saved = ConsultationRequest.objects.get()
    assert saved.kind == Kind.FARM_VISIT and saved.village_or_address == VILLAGE and saved.crop is not None


def test_the_thank_you_page_says_so_and_keeps_the_call_button(client):
    response = client.get(THANKS)
    html = response.content.decode()
    assert response.status_code == 200
    assert RECEIVED in html
    assert "\u0628\u0647\u200c\u0632\u0648\u062f\u06cc \u0628\u0627 \u0634\u0645\u0627 \u062a\u0645\u0627\u0633 \u0645\u06cc\u200c\u06af\u06cc\u0631\u06cc\u0645" in html  # we will call you back
    section = re.search(r"<section.*?</section>", html, re.S).group(0)
    button = re.search(rf"<a {re.escape(TEL)} class=\"([^\"]*)\"", section)
    assert button and "hidden" not in button.group(1).split()


def test_the_visitor_follows_the_redirect_to_the_thank_you_page(client):
    response = client.post(URL, question(), follow=True)
    assert RECEIVED in response.content.decode()


def test_nothing_is_sent_by_a_plain_get(client):
    client.get(URL)
    client.get(THANKS)
    assert ConsultationRequest.objects.count() == 0


def test_an_invalid_post_shows_the_errors_keeps_what_was_typed_and_stores_nothing(client):
    response = client.post(URL, question(phone="12345", message=ASK))
    html = response.content.decode()
    assert response.status_code == 200
    assert ConsultationRequest.objects.count() == 0
    assert "text-red-700" in html
    assert ASK in html and NAME in html and 'value="12345"' in html


def test_a_question_without_its_text_is_refused_with_a_message_on_the_field(client):
    html = client.post(URL, question(message="")).content.decode()
    assert ConsultationRequest.objects.count() == 0
    assert re.search(r'id="id_message".*?text-red-700', html, re.S)


def test_a_farm_visit_without_an_address_is_refused(client):
    client.post(URL + "?kind=farm_visit", visit(village_or_address=""))
    assert ConsultationRequest.objects.count() == 0


def test_a_post_without_the_csrf_token_is_refused():
    strict = Client(enforce_csrf_checks=True)
    assert strict.post(URL, question()).status_code == 403
    assert ConsultationRequest.objects.count() == 0


def test_the_kind_in_the_posted_data_is_ignored(client):
    client.post(URL, question(kind="farm_visit"))
    assert ConsultationRequest.objects.get().kind == Kind.QUESTION


# --- the honeypot ---------------------------------------------------------------------------------------


def test_a_filled_honeypot_looks_like_success_but_stores_nothing(client):
    response = client.post(URL, question(website="http://spam.example"))
    assert response.status_code == 302 and response.url == THANKS
    assert ConsultationRequest.objects.count() == 0


def test_a_filled_honeypot_is_not_counted_against_the_limit(client):
    for _ in range(SUBMISSION_LIMIT + 3):
        client.post(URL, question(website="x"))
    assert client.post(URL, question()).status_code == 302
    assert ConsultationRequest.objects.count() == 1


# --- the limit ----------------------------------------------------------------------------------------------


def test_the_submissions_up_to_the_limit_are_stored_and_the_next_is_refused(client):
    for _ in range(SUBMISSION_LIMIT):
        assert client.post(URL, question()).status_code == 302
    response = client.post(URL, question(message="\u067e\u0631\u0633\u0634 \u0634\u0634\u0645"))
    assert response.status_code == 429
    assert ConsultationRequest.objects.count() == SUBMISSION_LIMIT


def test_the_limited_page_explains_keeps_what_was_typed_and_offers_the_call_button(client):
    for _ in range(SUBMISSION_LIMIT):
        client.post(URL, question())
    typed = "\u067e\u0631\u0633\u0634 \u0634\u0634\u0645"
    html = client.post(URL, question(message=typed)).content.decode()
    section = re.search(r'<section id="limited".*?</section>', html, re.S).group(0)
    assert LIMITED in section
    button = re.search(rf"<a {re.escape(TEL)} class=\"([^\"]*)\"", section)
    assert button and "hidden" not in button.group(1).split()
    assert typed in html  # not lost


def test_another_visitor_is_not_affected(client):
    for _ in range(SUBMISSION_LIMIT + 1):
        client.post(URL, question())
    other = Client(REMOTE_ADDR="198.51.100.20")
    assert other.post(URL, question()).status_code == 302


def test_behind_the_proxy_visitors_are_told_apart_by_the_header(settings):
    settings.CLIENT_IP_HEADER = "HTTP_X_REAL_IP"
    first = Client(REMOTE_ADDR="127.0.0.1", HTTP_X_REAL_IP="198.51.100.1")
    second = Client(REMOTE_ADDR="127.0.0.1", HTTP_X_REAL_IP="198.51.100.2")
    for _ in range(SUBMISSION_LIMIT + 1):
        first.post(URL, question())
    assert first.post(URL, question()).status_code == 429
    assert second.post(URL, question()).status_code == 302


def test_reading_the_form_is_never_limited(client):
    for _ in range(SUBMISSION_LIMIT + 3):
        client.post(URL, question())
    assert client.get(URL).status_code == 200
    assert client.get(THANKS).status_code == 200


def test_invalid_posts_count_too(client):
    for _ in range(SUBMISSION_LIMIT):
        client.post(URL, question(phone="1"))
    assert client.post(URL, question()).status_code == 429


# --- telling the store (D42) -------------------------------------------------------------------------


TELEGRAM = "\u062a\u0644\u06af\u0631\u0627\u0645"  # تلگرام


@pytest.fixture
def telegram(settings, monkeypatch):
    """A configured, faked Telegram: gives back the texts that were sent."""
    settings.TELEGRAM_BOT_TOKEN = "123456789:AAHnot-a-real-token"
    settings.TELEGRAM_CHAT_ID = "-1001234567890"
    sent = []
    monkeypatch.setattr(notifications, "post_to_telegram", lambda text: sent.append(text))
    return sent


def refuse(monkeypatch, reason=None):
    """Make the channel answer with a refusal instead."""
    reason = reason or notifications.REJECTED

    def sender(text):
        raise notifications.NotificationError(reason)

    monkeypatch.setattr(notifications, "post_to_telegram", sender)


def test_a_sent_notification_is_recorded_on_the_request(client, telegram):
    response = client.post(URL, question())
    assert response.status_code == 302 and response.url == THANKS
    saved = ConsultationRequest.objects.get()
    assert (saved.notification_status, saved.notification_detail) == (NotificationStatus.SENT, "")
    assert len(telegram) == 1 and ASK in telegram[0]


def test_a_failed_notification_is_recorded_and_the_visitor_still_reaches_the_thank_you_page(
    client, telegram, monkeypatch
):
    refuse(monkeypatch)
    response = client.post(URL, question())
    assert response.status_code == 302 and response.url == THANKS
    saved = ConsultationRequest.objects.get()
    assert (saved.notification_status, saved.notification_detail) == (NotificationStatus.FAILED, notifications.REJECTED)


def test_the_visitor_still_reaches_the_thank_you_page_when_the_notifier_itself_breaks(client, telegram, monkeypatch):
    def explode(consultation):
        raise RuntimeError("a bug in the notifier")

    monkeypatch.setattr(views, "send_consultation_notification", explode)
    html = client.post(URL, question(), follow=True).content.decode()
    assert RECEIVED in html
    saved = ConsultationRequest.objects.get()
    assert (saved.notification_status, saved.notification_detail) == (NotificationStatus.FAILED, CRASHED)


def test_the_thank_you_page_says_nothing_about_the_notification(client, telegram, monkeypatch):
    refuse(monkeypatch)
    html = client.post(URL, question(), follow=True).content.decode()
    assert RECEIVED in html
    assert TELEGRAM not in html and CRASHED not in html


def test_without_a_bot_the_request_is_stored_and_says_why_nothing_was_sent(client):
    response = client.post(URL, question())
    assert response.status_code == 302
    saved = ConsultationRequest.objects.get()
    assert (saved.notification_status, saved.notification_detail) == (
        NotificationStatus.NOT_ATTEMPTED,
        NOT_CONFIGURED,
    )


def test_the_notification_costs_one_update_and_leaves_the_customers_words_alone(client, telegram):
    with CaptureQueriesContext(connection) as queries:
        client.post(URL, question())
    assert len([query for query in queries if query["sql"].startswith("UPDATE")]) == 1
    saved = ConsultationRequest.objects.get()
    assert (saved.kind, saved.name, saved.phone, saved.message) == (Kind.QUESTION, NAME, "09121234567", ASK)
    assert saved.status == ConsultationRequest.Status.NEW


def test_a_bot_submission_notifies_nobody(client, telegram):
    client.post(URL, question(website="http://spam.example"))
    assert telegram == []


def test_a_refused_submission_notifies_nobody(client, telegram):
    for _ in range(SUBMISSION_LIMIT):
        client.post(URL, question())
    telegram.clear()
    assert client.post(URL, question()).status_code == 429
    assert telegram == []
