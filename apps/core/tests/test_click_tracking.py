"""Tests for tap counting (D16, resolved as D44).

ClickEvent itself is in apps/core/models.py, the redirect-through view is
apps/core/views.py, and the template tag that builds the tracked href is
apps/core/templatetags/clicks.py. Together: a call/WhatsApp/Telegram/Rubika
button points at /click/<kind>/?from=<page>, which logs one ClickEvent and
redirects to the real destination -- no JavaScript needed.
"""
from urllib.parse import quote

import pytest
from django.contrib.auth import get_user_model
from django.template import RequestContext, Template
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.core.models import ClickEvent, SiteSettings

pytestmark = pytest.mark.django_db

Kind = ClickEvent.Kind


def click_url(kind):
    return reverse("core:track_click", args=[kind])


# --- the model --------------------------------------------------------------------------------


def test_the_four_kinds():
    assert set(Kind.values) == {"call", "whatsapp", "telegram", "rubika"}


def test_no_personal_data_is_kept():
    # Only what, where, when -- never an IP address or a user agent.
    field_names = {f.name for f in ClickEvent._meta.get_fields()}
    assert field_names == {"id", "kind", "page_path", "created_at"}


def test_str_names_the_kind_and_the_page():
    event = ClickEvent.objects.create(kind=Kind.CALL, page_path="/products/")
    assert str(event) == "تماس - /products/"


def test_str_of_an_event_with_no_page_path():
    event = ClickEvent.objects.create(kind=Kind.CALL, page_path="")
    assert str(event) == "تماس - -"


def test_newest_first():
    first = ClickEvent.objects.create(kind=Kind.CALL)
    second = ClickEvent.objects.create(kind=Kind.CALL)
    assert list(ClickEvent.objects.all()) == [second, first]


# --- the view: logs one event, then redirects --------------------------------------------------


def test_a_call_tap_is_logged_and_redirected_to_the_tel_link(client):
    response = client.get(click_url("call"), {"from": "/products/"})
    assert response.status_code == 302
    assert response.url == "tel:+989112747628"
    event = ClickEvent.objects.get()
    assert (event.kind, event.page_path) == (Kind.CALL, "/products/")


def test_a_whatsapp_tap_is_logged_and_redirected():
    client = Client()
    response = client.get(click_url("whatsapp"), {"from": "/contact/"})
    assert response.status_code == 302
    assert response.url == "https://wa.me/989112747628"
    assert ClickEvent.objects.get().kind == Kind.WHATSAPP


def test_a_telegram_tap_is_logged_and_redirected_once_a_username_is_set(client):
    site = SiteSettings.load()
    site.telegram_username = "store_test"
    site.save()
    response = client.get(click_url("telegram"), {"from": "/contact/"})
    assert response.status_code == 302
    assert response.url == "https://t.me/store_test"
    assert ClickEvent.objects.get().kind == Kind.TELEGRAM


def test_a_rubika_tap_is_logged_and_redirected_once_a_link_is_set(client):
    site = SiteSettings.load()
    site.rubika_url = "https://rubika.ir/example"
    site.save()
    response = client.get(click_url("rubika"), {"from": "/contact/"})
    assert response.status_code == 302
    assert response.url == "https://rubika.ir/example"
    assert ClickEvent.objects.get().kind == Kind.RUBIKA


def test_a_missing_from_is_stored_as_an_empty_page_path(client):
    client.get(click_url("call"))
    assert ClickEvent.objects.get().page_path == ""


def test_an_overlong_from_is_cut_not_refused(client):
    client.get(click_url("call"), {"from": "/x" * 500})
    assert len(ClickEvent.objects.get().page_path) == 255


def test_an_unknown_kind_is_a_404(client):
    response = client.get("/click/sms/")
    assert response.status_code == 404
    assert ClickEvent.objects.count() == 0


def test_a_kind_whose_setting_is_empty_goes_home_without_logging_anything(client):
    # The Telegram username is empty by default, so the button never renders
    # -- but a tap still must not land nowhere if it somehow happens.
    response = client.get(click_url("telegram"))
    assert response.status_code == 302
    assert response.url == reverse("pages:home")
    assert ClickEvent.objects.count() == 0


def test_a_tap_is_never_rejected_for_csrf_its_a_plain_get(client):
    response = client.get(click_url("call"))
    assert response.status_code == 302


# --- the template tag --------------------------------------------------------------------------


def _rendered_href(path):
    request = RequestFactory().get(path)
    template = Template("{% load clicks %}{% click_url 'call' %}")
    return template.render(RequestContext(request))


def test_the_tag_points_at_the_tracking_view_with_the_current_path():
    assert _rendered_href("/products/") == f"{click_url('call')}?from=/products/"


def test_the_tag_percent_encodes_a_persian_path():
    path = "/products/\u0627\u0633\u06a9\u0648\u0631/"  # /products/اسکور/
    href = _rendered_href(path)
    assert href == f"{click_url('call')}?from={quote(path)}"
    assert href != f"{click_url('call')}?from={path}"  # it really was encoded


def test_the_tag_is_used_on_the_home_page(client):
    html = client.get(reverse("pages:home")).content.decode()
    assert f'href="{click_url("call")}?from={quote("/")}"' in html


# --- the admin: a read-only log --------------------------------------------------------------


@pytest.fixture
def admin_client():
    user = get_user_model().objects.create_superuser("boss", "boss@example.com", "pw-for-tests-123")
    adapter = Client()
    adapter.force_login(user)
    return adapter


@pytest.fixture
def staff_client():
    user = get_user_model().objects.create_user("helper", password="pw-for-tests-123", is_staff=True)
    adapter = Client()
    adapter.force_login(user)
    return adapter


def test_the_changelist_opens_for_an_admin(admin_client):
    ClickEvent.objects.create(kind=Kind.CALL, page_path="/products/")
    response = admin_client.get(reverse("admin:core_clickevent_changelist"))
    assert response.status_code == 200


def test_staff_without_permission_is_refused(staff_client):
    assert staff_client.get(reverse("admin:core_clickevent_changelist")).status_code == 403


def test_nobody_can_add_one_from_the_admin(admin_client):
    assert admin_client.get(reverse("admin:core_clickevent_add")).status_code == 403


def test_the_change_page_has_nothing_left_to_save(admin_client):
    # has_change_permission is always False, so even a superuser only gets a
    # read-only page here -- Django still renders it (200), just without a
    # save button, since the superuser's own view permission is separate.
    event = ClickEvent.objects.create(kind=Kind.CALL)
    response = admin_client.get(reverse("admin:core_clickevent_change", args=[event.pk]))
    assert response.status_code == 200
    assert "_save" not in response.content.decode()


def test_the_list_can_be_filtered_by_kind(admin_client):
    ClickEvent.objects.create(kind=Kind.CALL)
    ClickEvent.objects.create(kind=Kind.WHATSAPP)
    html = admin_client.get(reverse("admin:core_clickevent_changelist")).content.decode()
    assert "kind__exact=call" in html
    assert "kind__exact=whatsapp" in html
