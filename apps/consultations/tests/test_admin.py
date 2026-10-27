import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Crop
from apps.consultations.admin import format_jalali_datetime
from apps.consultations.models import ConsultationRequest

pytestmark = pytest.mark.django_db

Kind = ConsultationRequest.Kind
Status = ConsultationRequest.Status
UTC = datetime.timezone.utc
PHONE = "09112747628"


@pytest.fixture
def admin_client():
    user = get_user_model().objects.create_superuser("boss", "boss@example.com", "pw-for-tests-123")
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def staff_client():
    """A staff member with no permissions at all."""
    user = get_user_model().objects.create_user("helper", password="pw-for-tests-123", is_staff=True)
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def view_only_client():
    user = get_user_model().objects.create_user("viewer", password="pw-for-tests-123", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="view_consultationrequest"))
    client = Client()
    client.force_login(user)
    return client


def url(view, *args):
    return reverse(f"admin:consultations_consultationrequest_{view}", args=args)


def make(**overrides):
    base = {"kind": Kind.QUESTION, "name": "\u0639\u0644\u06cc", "phone": PHONE, "message": "\u0633\u0644\u0627\u0645"}
    return ConsultationRequest.objects.create(**{**base, **overrides})


def at(request, when):
    """created_at is automatic, so move it with an update."""
    ConsultationRequest.objects.filter(pk=request.pk).update(created_at=when)
    request.refresh_from_db()
    return request


def action(client, name, *requests):
    return client.post(
        url("changelist"),
        {"action": name, "_selected_action": [r.pk for r in requests]},
        follow=True,
    )


def names(response):
    return [r.name for r in response.context["cl"].result_list]


# --- access ----------------------------------------------------------------------------------


def test_changelist_opens(admin_client):
    assert admin_client.get(url("changelist")).status_code == 200


def test_staff_without_permission_is_refused(staff_client):
    assert staff_client.get(url("changelist")).status_code == 403


def test_nobody_can_add_a_request_from_the_admin(admin_client):
    assert admin_client.get(url("add")).status_code == 403


# --- the change page ----------------------------------------------------------------------------


def test_only_the_status_is_editable_on_the_change_page(admin_client):
    request = make()
    html = admin_client.get(url("change", request.pk)).content.decode()
    assert 'name="status"' in html
    for field in ("kind", "name", "phone", "message", "crop", "village_or_address", "notification_status", "notification_detail"):
        assert f'name="{field}"' not in html


def test_the_change_page_shows_what_the_customer_wrote(admin_client):
    crop = Crop.objects.create(name="\u06af\u0646\u062f\u0645")
    request = make(message="\u0628\u0631\u06af\u0647\u0627 \u0632\u0631\u062f \u0634\u062f\u0647", crop=crop, village_or_address="\u0622\u0642\u200c\u0622\u0628\u0627\u062f")
    html = admin_client.get(url("change", request.pk)).content.decode()
    assert "\u0628\u0631\u06af\u0647\u0627 \u0632\u0631\u062f \u0634\u062f\u0647" in html
    assert "\u06af\u0646\u062f\u0645" in html
    assert "\u0622\u0642\u200c\u0622\u0628\u0627\u062f" in html


def test_the_status_can_be_changed_from_the_change_page(admin_client):
    request = make()
    response = admin_client.post(url("change", request.pk), {"status": Status.HANDLED})
    assert response.status_code == 302
    request.refresh_from_db()
    assert request.status == Status.HANDLED
    assert request.name == "\u0639\u0644\u06cc"  # nothing else was touched


# --- the list ------------------------------------------------------------------------------------


def test_the_phone_is_a_tap_to_call_link_in_the_list_and_on_the_change_page(admin_client):
    request = make(phone="+98 911 274 7628")
    for page in (url("changelist"), url("change", request.pk)):
        html = admin_client.get(page).content.decode()
        assert 'href="tel:+989112747628"' in html
        assert "0911 274 7628" in html


def test_new_requests_come_first_then_handled_ones_each_newest_first(admin_client):
    # Created in this order, but dated so that the time order differs from the
    # creation order: the list has to go by time, not by id.
    newest_new = make(name="newest-new")
    handled = make(name="handled", status=Status.HANDLED)
    older_new = make(name="older-new")
    at(newest_new, datetime.datetime(2026, 3, 1, tzinfo=UTC))
    at(handled, datetime.datetime(2026, 4, 1, tzinfo=UTC))
    at(older_new, datetime.datetime(2026, 1, 1, tzinfo=UTC))
    assert names(admin_client.get(url("changelist"))) == ["newest-new", "older-new", "handled"]


def test_the_list_can_be_filtered_by_status_and_kind(admin_client):
    make(name="open")
    make(name="done", status=Status.HANDLED)
    make(name="visit", **{"kind": Kind.FARM_VISIT, "message": "", "village_or_address": "x"})
    assert set(names(admin_client.get(url("changelist"), {"status__exact": "handled"}))) == {"done"}
    assert set(names(admin_client.get(url("changelist"), {"kind__exact": "farm_visit"}))) == {"visit"}


def test_the_sidebar_offers_the_status_and_kind_filters(admin_client):
    make()
    html = admin_client.get(url("changelist")).content.decode()
    assert "status__exact=new" in html
    assert "status__exact=handled" in html
    assert "kind__exact=farm_visit" in html


def test_the_time_is_shown_in_jalali_for_the_store_time_zone(admin_client):
    # 1 Farvardin 1405 is 21 March 2026. Tehran is UTC+3:30 all year.
    request = make()
    at(request, datetime.datetime(2026, 3, 21, 12, 0, tzinfo=UTC))
    html = admin_client.get(url("changelist")).content.decode()
    assert "1405/01/01 15:30" in html


def test_the_jalali_time_helper_crosses_midnight_in_store_time():
    # 21:00 UTC is 00:30 the next day in Tehran, so the date moves on too.
    value = datetime.datetime(2026, 3, 21, 21, 0, tzinfo=UTC)
    assert format_jalali_datetime(value) == "1405/01/02 00:30"


# --- search ----------------------------------------------------------------------------------------


def test_search_finds_a_phone_typed_with_persian_digits(admin_client):
    make(name="a", phone="09112747628")
    make(name="b", phone="09121234567")
    typed = "\u06f0\u06f9\u06f1\u06f1\u06f2\u06f7\u06f4"  # 0911274
    assert names(admin_client.get(url("changelist"), {"q": typed})) == ["a"]


def test_search_finds_a_name_typed_with_an_arabic_kaf(admin_client):
    make(name="\u06a9\u0631\u06cc\u0645")
    make(name="\u0639\u0644\u06cc")
    assert names(admin_client.get(url("changelist"), {"q": "\u0643\u0631\u06cc\u0645"})) == ["\u06a9\u0631\u06cc\u0645"]


def test_search_looks_in_the_message_and_the_address(admin_client):
    make(name="a", message="\u0633\u0646 \u06af\u0646\u062f\u0645")
    make(name="b", **{"kind": Kind.FARM_VISIT, "message": "", "village_or_address": "\u0622\u0642\u200c\u0622\u0628\u0627\u062f"})
    assert names(admin_client.get(url("changelist"), {"q": "\u0633\u0646"})) == ["a"]
    assert names(admin_client.get(url("changelist"), {"q": "\u0622\u0642\u200c\u0622\u0628\u0627\u062f"})) == ["b"]


def test_every_word_of_a_search_has_to_match(admin_client):
    make(name="a", message="\u0633\u0646 \u06af\u0646\u062f\u0645")
    make(name="b", message="\u0633\u0646 \u062c\u0648")
    assert names(admin_client.get(url("changelist"), {"q": "\u0633\u0646 \u06af\u0646\u062f\u0645"})) == ["a"]


# --- actions ------------------------------------------------------------------------------------------


def test_mark_handled_changes_the_selected_new_requests(admin_client):
    picked = make(name="picked")
    left = make(name="left")
    response = action(admin_client, "mark_handled", picked)
    picked.refresh_from_db()
    left.refresh_from_db()
    assert (picked.status, left.status) == (Status.HANDLED, Status.NEW)
    assert "1 \u062f\u0631\u062e\u0648\u0627\u0633\u062a \u00ab\u0631\u0633\u06cc\u062f\u06af\u06cc \u0634\u062f\u00bb" in response.content.decode()


def test_mark_handled_counts_only_what_it_changed(admin_client):
    new = make(name="n")
    done = make(name="d", status=Status.HANDLED)
    response = action(admin_client, "mark_handled", new, done)
    html = response.content.decode()
    assert "1 \u062f\u0631\u062e\u0648\u0627\u0633\u062a \u00ab\u0631\u0633\u06cc\u062f\u06af\u06cc \u0634\u062f\u00bb" in html
    assert "2 \u062f\u0631\u062e\u0648\u0627\u0633\u062a \u00ab\u0631\u0633\u06cc\u062f\u06af\u06cc \u0634\u062f\u00bb" not in html


def test_mark_new_undoes_a_mistaken_tap(admin_client):
    done = make(status=Status.HANDLED)
    action(admin_client, "mark_new", done)
    done.refresh_from_db()
    assert done.status == Status.NEW


def test_the_actions_are_offered_to_someone_who_can_change(admin_client):
    make()  # the action bar is only drawn when the list has rows
    html = admin_client.get(url("changelist")).content.decode()
    assert 'value="mark_handled"' in html
    assert 'value="mark_new"' in html


def test_someone_with_view_only_rights_cannot_run_the_actions(view_only_client):
    request = make()
    html = view_only_client.get(url("changelist")).content.decode()
    assert 'value="mark_handled"' not in html
    action(view_only_client, "mark_handled", request)
    request.refresh_from_db()
    assert request.status == Status.NEW
