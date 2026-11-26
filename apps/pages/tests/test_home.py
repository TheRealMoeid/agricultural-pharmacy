"""Tests for the home page (D45) and, through it, the base template."""
import re

import pytest
from django.urls import reverse

from apps.core.models import SiteSettings

pytestmark = pytest.mark.django_db

# Call buttons go through the click-tracking redirect (D16/D44).
CALL = 'href="/click/call/?from=/"'


def get_home(client):
    response = client.get(reverse("pages:home"))
    assert response.status_code == 200
    return response.content.decode()


def test_the_home_page_is_the_root_of_the_site():
    assert reverse("pages:home") == "/"


def test_the_page_is_persian_and_right_to_left(client):
    assert '<html lang="fa" dir="rtl"' in get_home(client)


def test_the_store_details_come_from_the_site_settings(client):
    site = SiteSettings.load()
    html = get_home(client)
    assert f"<title>{site.store_name}</title>" in html
    assert site.address in html
    assert site.working_hours in html


def test_changing_the_settings_changes_the_page(client):
    site = SiteSettings.load()
    site.store_name = "نام آزمایشی"
    site.phone = "09121234567"
    site.save()
    html = get_home(client)
    assert "<title>نام آزمایشی</title>" in html
    assert "0912 123 4567" in html


# --- the content of the home page -------------------------------------------------------


def test_the_page_has_a_one_line_pitch(client):
    html = get_home(client)
    assert "فروش سموم و کودهای تقویتی کشاورزی" in html


def test_the_page_links_to_products_experts_consultation_and_contact(client):
    html = get_home(client)
    for name in ("catalog:product_list", "pages:experts", "consultations:form", "pages:contact"):
        assert f'href="{reverse(name)}"' in html


def test_the_home_page_has_no_hero_and_no_duplicate_call_button(client):
    # The call bar, header and footer already carry the number. The home page
    # itself must not add a fourth call link (D45, simplified).
    html = get_home(client)
    main = re.search(r"<main[^>]*>(.*?)</main>", html, re.S).group(1)
    assert CALL not in main
    assert "min-h-14" not in main


def test_the_call_link_is_in_the_header_the_call_bar_and_the_footer(client):
    assert get_home(client).count(CALL) == 3


def test_no_template_comment_leaks_into_the_page(client):
    assert "{#" not in get_home(client)


def test_there_is_no_price_anywhere_on_the_home_page(client):
    html = get_home(client)
    assert "\u0642\u06cc\u0645\u062a" not in html  # قیمت
    assert "\u062a\u0648\u0645\u0627\u0646" not in html  # تومان


def test_the_header_menu_links_are_left_off_the_home_page_only(client):
    # The home page has its own cards for these links; every other page keeps the menu.
    header = re.search(r"<header.*?</header>", get_home(client), re.S).group(0)
    for name in ("catalog:product_list", "pages:experts", "consultations:form", "pages:contact"):
        assert f'href="{reverse(name)}"' not in header
    other = client.get(reverse("pages:contact")).content.decode()
    other_header = re.search(r"<header.*?</header>", other, re.S).group(0)
    assert f'href="{reverse("catalog:product_list")}"' in other_header


# --- calling is the easiest thing on every page ---------------------------------------


def test_the_call_bar_is_for_phones_and_the_header_button_for_wide_screens(client):
    html = get_home(client)
    bar = re.search(r'<div id="call-bar" class="([^"]*)"', html)
    assert bar, "the call bar is missing"
    assert "fixed" in bar.group(1).split() and "bottom-0" in bar.group(1).split()
    assert "md:hidden" in bar.group(1).split()
    header_button = re.search(r'<a href="/click/call/[^"]*" class="([^"]*)"', html)
    classes = header_button.group(1).split()
    assert "hidden" in classes and "md:inline-flex" in classes


def test_the_page_leaves_room_for_the_call_bar_on_phones(client):
    body = re.search(r"<body class=\"([^\"]*)\"", get_home(client)).group(1).split()
    assert "pb-24" in body
    assert "md:pb-0" in body


def test_the_phone_number_is_shown_left_to_right_inside_the_right_to_left_page(client):
    html = get_home(client)
    assert len(re.findall(r'<span dir="ltr"[^>]*>0911 274 7628</span>', html)) >= 2


# --- self-contained ----------------------------------------------------------------------


def test_the_page_loads_nothing_from_other_websites(client):
    html = get_home(client)
    assert not re.search(r'(?:src|href|action)=["\']?(?:https?:)?//', html)
    assert "@import" not in html


def test_the_page_uses_our_own_stylesheet_and_preloads_the_regular_font(client):
    html = get_home(client)
    assert '<link rel="stylesheet" href="/static/css/site.css">' in html
    assert 'rel="preload" href="/static/fonts/Vazirmatn-Regular.woff2" as="font" type="font/woff2" crossorigin' in html
    assert "Vazirmatn-Bold" not in html


def test_the_store_name_is_in_the_header(client):
    html = get_home(client)
    header = re.search(r"<header.*?</header>", html, re.S).group(0)
    assert SiteSettings.load().store_name in header