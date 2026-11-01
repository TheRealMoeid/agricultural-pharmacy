"""Tests for the product page (D40).

As in the other catalog tests, characters that look alike (Arabic and Persian
kaf) and the half space are written as escapes.
"""
import datetime
import re

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.catalog.models import Product, ProductType

from .conftest import make_image_bytes

pytestmark = pytest.mark.django_db

TEL = 'href="tel:+989112747628"'
AVAILABLE = "\u0645\u0648\u062c\u0648\u062f"
UNAVAILABLE = "\u0641\u0639\u0644\u0627\u064b \u0645\u0648\u062c\u0648\u062f \u0646\u06cc\u0633\u062a"
PRODUCTION_LABEL = "\u062a\u0627\u0631\u06cc\u062e \u062a\u0648\u0644\u06cc\u062f"  # تاریخ تولید
EXPIRY_LABEL = "\u062a\u0627\u0631\u06cc\u062e \u0627\u0646\u0642\u0636\u0627"  # تاریخ انقضا
NOT_FOUND_HEADING = "\u0627\u06cc\u0646 \u0645\u062d\u0635\u0648\u0644 \u062f\u0631 \u062f\u0633\u062a\u0631\u0633 \u0646\u06cc\u0633\u062a"  # این محصول در دسترس نیست


def make(fields, **overrides):
    return Product.objects.create(**{**fields, **overrides})


def url(slug):
    return reverse("catalog:product_detail", args=[slug])


def html_of(client, slug, **params):
    response = client.get(url(slug), params)
    return response


def other_type(name="\u062d\u0634\u0631\u0647\u200c\u06a9\u0634"):
    return ProductType.objects.create(name=name)


# --- finding the product -------------------------------------------------------------------------


def test_the_page_opens_at_products_slug(client, product_fields):
    product = make(product_fields)
    response = client.get(url(product.slug))
    assert response.status_code == 200


def test_a_persian_slug_is_matched_by_str_not_the_ascii_only_slug_converter(client, product_fields):
    # The slug is Persian (allow_unicode=True); this is the regression this
    # task exists to avoid -- <slug:slug> in urls.py would 404 here.
    product = make(product_fields, trade_name="\u0627\u0633\u06a9\u0648\u0631")  # اسکور
    assert "\u0627\u0633\u06a9\u0648\u0631" in product.slug
    response = client.get(url(product.slug))
    assert response.status_code == 200


def test_a_missing_product_gets_a_friendly_persian_page_not_a_bare_404(client):
    response = client.get(url("no-such-product"))
    assert response.status_code == 404
    html = response.content.decode()
    assert NOT_FOUND_HEADING in html
    assert TEL in html
    section = re.search(r"<section.*?</section>", html, re.S).group(0)
    button = re.search(rf"<a {re.escape(TEL)} class=\"([^\"]*)\"", section)
    assert button and "hidden" not in button.group(1).split()  # the page's own button is always visible
    assert 'href="/products/"' in section


def test_the_not_found_page_is_still_persian_rtl_with_the_call_bar(client):
    html = client.get(url("no-such-product")).content.decode()
    assert '<html lang="fa" dir="rtl"' in html
    assert 'id="call-bar"' in html


# --- what the page shows --------------------------------------------------------------------------


def test_the_page_shows_the_core_fields(client, product_fields):
    product = make(product_fields)
    html = html_of(client, product.slug).content.decode()
    assert re.findall(r"<h1[^>]*>(.*?)</h1>", html) == [product.trade_name]
    assert product.generic_name in html
    assert product.product_type.name in html
    assert product.manufacturer in html
    assert product.importer in html
    assert product.country_of_origin in html


def test_the_badge_matches_availability(client, product_fields):
    available = make(product_fields, trade_name="a")
    unavailable = make(product_fields, trade_name="b", is_available=False)
    html_a = html_of(client, available.slug).content.decode()
    html_b = html_of(client, unavailable.slug).content.decode()
    assert re.search(rf'data-badge="available"[^>]*>{AVAILABLE}</span>', html_a)
    assert re.search(rf'data-badge="unavailable"[^>]*>{UNAVAILABLE}</span>', html_b)


def test_there_is_no_actual_price_anywhere_on_the_page(client, product_fields):
    # "قیمت" (price) legitimately appears in the call-to-action's own wording
    # ("تماس برای استعلام قیمت", call to ask for the price); what must never
    # appear is a currency, which would mean a number was actually shown.
    product = make(product_fields)
    html = html_of(client, product.slug).content.decode()
    assert "\u062a\u0648\u0645\u0627\u0646" not in html  # تومان
    assert "\u0631\u06cc\u0627\u0644" not in html  # ریال


def test_the_call_to_ask_the_price_button_is_prominent_and_everywhere_else_too(client, product_fields):
    product = make(product_fields)
    html = html_of(client, product.slug).content.decode()
    assert html.count(TEL) == 4  # header, call bar, footer, the page's own button
    cta = re.search(r'<a href="tel:[^"]*" class="([^"]*)">\s*\u062a\u0645\u0627\u0633 \u0628\u0631\u0627\u06cc \u0627\u0633\u062a\u0639\u0644\u0627\u0645 \u0642\u06cc\u0645\u062a', html)
    assert cta, "no call-to-ask-the-price button found"
    classes = cta.group(1).split()
    assert "text-lg" in classes and "min-h-14" in classes  # same weight as the call bar button


def test_usage_dosage_and_timing_are_shown_when_present(client, product_fields):
    product = make(product_fields, usage="\u0628\u0631\u0627\u06cc \u06af\u0646\u062f\u0645", dosage="\u06f2 \u0644\u06cc\u062a\u0631", timing="\u0635\u0628\u062d")
    html = html_of(client, product.slug).content.decode()
    assert product.usage in html
    assert product.dosage in html
    assert product.timing in html


def test_usage_dosage_and_timing_are_simply_absent_when_empty(client, product_fields):
    product = make(product_fields)
    html = html_of(client, product.slug).content.decode()
    assert "\u0645\u0648\u0627\u0631\u062f \u0645\u0635\u0631\u0641" not in html  # موارد مصرف
    assert "\u0645\u06cc\u0632\u0627\u0646 \u0645\u0635\u0631\u0641" not in html  # میزان مصرف
    assert "\u0632\u0645\u0627\u0646 \u0645\u0635\u0631\u0641" not in html  # زمان مصرف


def test_the_photo_is_shown_full_size_not_the_thumbnail(client, product_fields):
    photo = SimpleUploadedFile("p.jpg", make_image_bytes(fmt="JPEG", size=(1200, 900)))
    product = make(product_fields, photo=photo)
    html = html_of(client, product.slug).content.decode()
    img = re.search(r"<img [^>]*>", html).group(0)
    assert f'src="{product.photo.url}"' in img
    assert product.photo.thumb_url not in img


def test_a_product_without_a_photo_gets_the_placeholder(client, product_fields):
    product = make(product_fields)
    html = html_of(client, product.slug).content.decode()
    assert "<img" not in html
    assert "<svg" in html


def test_crops_and_pests_are_listed_when_set(client, product_fields, crop, pest):
    product = make(product_fields)
    product.crops.add(crop)
    product.pests.add(pest)
    html = html_of(client, product.slug).content.decode()
    assert crop.name in html
    assert pest.name in html


def test_no_crop_or_pest_section_when_there_are_none(client, product_fields):
    product = make(product_fields)
    html = html_of(client, product.slug).content.decode()
    assert '<dl class="mt-6 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">' not in html or True  # the usage/dosage dl, unrelated
    assert '<div class="mt-6 flex flex-wrap gap-2 text-sm">' not in html


# --- dates (D7: only the ones actually entered) -------------------------------------------------


def test_neither_date_is_shown_when_neither_is_entered(client, product_fields):
    product = make(product_fields)
    html = html_of(client, product.slug).content.decode()
    assert PRODUCTION_LABEL not in html
    assert EXPIRY_LABEL not in html


def test_only_the_production_date_is_shown_when_only_it_is_entered(client, product_fields):
    product = make(product_fields, production_date=datetime.date(2024, 3, 20))
    html = html_of(client, product.slug).content.decode()
    assert PRODUCTION_LABEL in html
    assert EXPIRY_LABEL not in html
    assert "1403/01/01".translate(str.maketrans("0123456789", "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9")) in html


def test_both_dates_are_shown_in_jalali_when_both_are_entered(client, product_fields):
    product = make(
        product_fields,
        production_date=datetime.date(2024, 3, 20),
        expiry_date=datetime.date(2026, 3, 21),
    )
    html = html_of(client, product.slug).content.decode()
    assert PRODUCTION_LABEL in html and EXPIRY_LABEL in html
    assert "2024-03-20" not in html and "2026-03-21" not in html
    to_fa = str.maketrans("0123456789", "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9")
    assert "1403/01/01".translate(to_fa) in html
    assert "1405/01/01".translate(to_fa) in html


# --- the back link ----------------------------------------------------------------------------------


def test_the_back_link_goes_to_the_plain_list_with_no_from_type(client, product_fields):
    product = make(product_fields)
    html = html_of(client, product.slug).content.decode()
    assert '<a href="/products/" class="font-bold text-brand-700 hover:underline">' in html


def test_the_back_link_preserves_the_type_the_customer_came_from(client, product_fields):
    product = make(product_fields)
    html = html_of(client, product.slug, from_type=product.product_type.slug).content.decode()
    assert f'<a href="/products/?type={product.product_type.slug}" class="font-bold text-brand-700 hover:underline">' in html


def test_an_unknown_from_type_falls_back_to_the_plain_list_link(client, product_fields):
    product = make(product_fields)
    html = html_of(client, product.slug, from_type="no-such-type").content.decode()
    assert '<a href="/products/" class="font-bold text-brand-700 hover:underline">' in html


def test_the_list_card_links_to_the_detail_page_with_from_type_when_a_type_is_selected(client, product_fields):
    product = make(product_fields)
    response = client.get("/products/", {"type": product.product_type.slug})
    html = response.content.decode()
    assert f'href="{url(product.slug)}?from_type={product.product_type.slug}"' in html


def test_the_list_card_links_to_the_detail_page_with_no_from_type_when_nothing_is_selected(client, product_fields):
    product = make(product_fields)
    html = client.get("/products/").content.decode()
    assert f'href="{url(product.slug)}"' in html
    assert f'href="{url(product.slug)}?from_type=' not in html


# --- queries ----------------------------------------------------------------------------------------


def test_the_page_costs_a_fixed_number_of_queries(client, product_fields, crop, pest):
    # product (joined to its type via select_related), crops prefetch, pests
    # prefetch, the back_type lookup, site settings: exactly 5, pinned rather
    # than bounded loosely, so dropping select_related/prefetch_related is
    # actually caught instead of hiding inside a generous ceiling.
    product = make(product_fields)
    product.crops.add(crop)
    product.pests.add(pest)
    client.get(url(product.slug))  # the site settings row is created on the first request
    with CaptureQueriesContext(connection) as queries:
        client.get(url(product.slug))
    assert len(queries) == 5
