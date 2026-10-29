"""Tests for the placeholder home page and, through it, the base template."""
import re

import pytest
from django.urls import reverse

from apps.core.models import SiteSettings

pytestmark = pytest.mark.django_db

TEL = 'href="tel:+989112747628"'


def get_home(client):
    response = client.get(reverse("pages:home"))
    assert response.status_code == 200
    return response.content.decode()


def test_the_home_page_is_the_root_of_the_site():
    assert reverse("pages:home") == "/"


def test_the_page_is_persian_and_right_to_left(client):
    html = get_home(client)
    assert '<html lang="fa" dir="rtl"' in html


def test_the_store_details_come_from_the_site_settings(client):
    site = SiteSettings.load()
    html = get_home(client)
    assert f"<title>{site.store_name}</title>" in html
    assert site.address in html
    assert site.working_hours in html


def test_the_home_page_has_one_heading_and_it_is_the_store_name(client):
    html = get_home(client)
    headings = re.findall(r"<h1[^>]*>(.*?)</h1>", html)
    assert headings == [SiteSettings.load().store_name]


def test_changing_the_settings_changes_the_page(client):
    site = SiteSettings.load()
    site.store_name = "نام آزمایشی"
    site.phone = "09121234567"
    site.save()
    html = get_home(client)
    assert "<title>نام آزمایشی</title>" in html
    assert 'href="tel:+989121234567"' in html
    assert "tel:+989112747628" not in html
    assert "0912 123 4567" in html


# --- calling is the easiest thing on every page ----------------------------------------------


def test_the_call_link_is_in_the_header_the_call_bar_and_the_footer(client):
    assert get_home(client).count(TEL) == 3


def test_the_call_bar_is_for_phones_and_the_header_button_for_wide_screens(client):
    html = get_home(client)
    bar = re.search(r'<div id="call-bar" class="([^"]*)"', html)
    assert bar, "the call bar is missing"
    assert "fixed" in bar.group(1).split() and "bottom-0" in bar.group(1).split()
    assert "md:hidden" in bar.group(1).split()
    header_button = re.search(r'<a href="tel:[^"]*" class="([^"]*)"', html)
    classes = header_button.group(1).split()
    assert "hidden" in classes and "md:inline-flex" in classes


def test_the_page_leaves_room_for_the_call_bar_on_phones(client):
    body = re.search(r"<body class=\"([^\"]*)\"", get_home(client)).group(1).split()
    assert "pb-24" in body
    assert "md:pb-0" in body


def test_the_phone_number_is_shown_left_to_right_inside_the_right_to_left_page(client):
    html = get_home(client)
    assert len(re.findall(r'<span dir="ltr"[^>]*>0911 274 7628</span>', html)) >= 2


# --- self-contained ------------------------------------------------------------------------------


def test_the_page_loads_nothing_from_other_websites(client):
    html = get_home(client)
    assert not re.search(r'(?:src|href|action)=["\']?(?:https?:)?//', html)
    assert "@import" not in html


def test_the_page_uses_our_own_stylesheet_and_preloads_the_regular_font(client):
    html = get_home(client)
    assert '<link rel="stylesheet" href="/static/css/site.css">' in html
    assert 'rel="preload" href="/static/fonts/Vazirmatn-Regular.woff2" as="font" type="font/woff2" crossorigin' in html
    assert "Vazirmatn-Bold" not in html  # bold is not on every page, so it is not preloaded
