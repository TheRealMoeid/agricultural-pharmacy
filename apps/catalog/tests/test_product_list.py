"""Tests for the public product list (D39).

As in the other catalog tests, characters that look alike (Arabic and Persian
kaf) and the half space are written as escapes.
"""
import re

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.http import urlencode

from apps.catalog.models import Crop, Pest, Product, ProductType
from apps.catalog.views import MAX_QUERY_LENGTH

from .conftest import make_image_bytes

pytestmark = pytest.mark.django_db

URL = "/products/"
AVAILABLE = "\u0645\u0648\u062c\u0648\u062f"  # موجود
UNAVAILABLE = "\u0641\u0639\u0644\u0627\u064b \u0645\u0648\u062c\u0648\u062f \u0646\u06cc\u0633\u062a"  # فعلاً موجود نیست
ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
SCORE = "\u0627\u0633" + PERSIAN_KAF + "\u0648\u0631"  # اسکور
SCORE_ARABIC_KAF = "\u0627\u0633" + ARABIC_KAF + "\u0648\u0631"
TEL = 'href="tel:+989112747628"'


def make(fields, **overrides):
    return Product.objects.create(**{**fields, **overrides})


def get(client, **params):
    response = client.get(URL, params)
    assert response.status_code == 200
    return response


def html_of(client, **params):
    return get(client, **params).content.decode()


def names(response):
    return [p.trade_name for p in response.context["products"]]


def chips(html):
    """(name, is_current) for every chip in the type filter."""
    nav = re.search(r"<nav[^>]*>(.*?)</nav>", html, re.S).group(1)
    return [
        (name, 'aria-current="true"' in attrs)
        for attrs, name in re.findall(r"<a href=\"[^\"]*\"([^>]*)>(.*?)</a>", nav, re.S)
    ]


def other_type(name="\u062d\u0634\u0631\u0647\u200c\u06a9\u0634"):  # حشره‌کش
    return ProductType.objects.create(name=name)


# --- the address and the page around the list --------------------------------------------------


def test_the_list_lives_at_products():
    assert reverse("catalog:product_list") == URL


def test_the_page_is_persian_rtl_and_titled_with_the_store_name(client, product_fields):
    make(product_fields)
    html = html_of(client)
    assert '<html lang="fa" dir="rtl"' in html
    assert re.search(r"<title>\s*\S.*\|", html)
    assert re.findall(r"<h1[^>]*>(.*?)</h1>", html) == ["\u0645\u062d\u0635\u0648\u0644\u0627\u062a"]  # محصولات


def test_calling_stays_easy_on_the_list_page(client, product_fields):
    make(product_fields)
    html = html_of(client)
    assert 'id="call-bar"' in html
    assert html.count(TEL) == 3  # header, call bar, footer


def test_the_page_loads_nothing_from_other_websites(client, product_fields):
    make(product_fields)
    html = html_of(client)
    assert not re.search(r'(?:src|href|action)=["\']?(?:https?:)?//', html)


def test_only_normal_and_bold_text_is_used(client, product_fields):
    make(product_fields)
    make(product_fields, trade_name="b", is_available=False)
    html = html_of(client)
    assert not re.search(r"font-(thin|extralight|light|medium|semibold|extrabold|black)", html)


def test_there_is_no_price_on_the_page(client, product_fields):
    make(product_fields)
    html = html_of(client)
    assert "\u0642\u06cc\u0645\u062a" not in html  # قیمت
    assert "\u062a\u0648\u0645\u0627\u0646" not in html  # تومان


def test_the_header_and_the_home_page_link_to_the_list(client):
    for page in ("/", URL):
        assert client.get(page).content.decode().count(f'href="{URL}"') >= 1
    assert client.get("/").content.decode().count(f'href="{URL}"') >= 2


# --- cards ---------------------------------------------------------------------------------------


def test_a_card_shows_the_names_the_type_and_the_availability(client, product_fields):
    make(product_fields)
    html = html_of(client)
    assert product_fields["trade_name"] in html
    assert product_fields["generic_name"] in html
    assert product_fields["product_type"].name in html
    assert re.search(rf'data-badge="available"[^>]*>{AVAILABLE}</span>', html)


def test_an_unavailable_product_stays_visible_with_a_clear_badge(client, product_fields):
    make(product_fields, trade_name="a", is_available=False)
    response = get(client)
    assert names(response) == ["a"]
    html = response.content.decode()
    assert re.search(rf'data-badge="unavailable"[^>]*>{UNAVAILABLE}</span>', html)
    assert 'data-badge="available"' not in html


def test_the_badge_is_text_not_only_colour(client, product_fields):
    make(product_fields, trade_name="a")
    make(product_fields, trade_name="b", is_available=False)
    html = html_of(client)
    assert AVAILABLE in html and UNAVAILABLE in html


def test_the_card_uses_the_thumbnail_not_the_main_photo(client, product_fields):
    photo = SimpleUploadedFile("p.jpg", make_image_bytes(fmt="JPEG", size=(1200, 900)))
    product = make(product_fields, photo=photo)
    html = html_of(client)
    img = re.search(r"<img [^>]*>", html).group(0)
    assert f'src="{product.photo.thumb_url}"' in img
    assert product.photo.url not in html.replace(product.photo.thumb_url, "")


def test_images_are_lazy_and_have_a_size_so_the_page_does_not_jump(client, product_fields):
    make(product_fields, photo=SimpleUploadedFile("p.jpg", make_image_bytes(fmt="JPEG", size=(300, 900))))
    img = re.search(r"<img [^>]*>", html_of(client)).group(0)
    assert 'loading="lazy"' in img
    assert 'width="320"' in img and 'height="320"' in img


def test_a_product_without_a_photo_gets_a_placeholder_and_no_img_tag(client, product_fields):
    make(product_fields)
    html = html_of(client)
    assert "<img" not in html
    assert re.search(r'<li data-product="\d+"[^>]*>\s*<div[^>]*>\s*<svg', html)


def test_every_card_has_the_same_square_box(client, product_fields):
    make(product_fields, trade_name="a")
    make(product_fields, trade_name="b", photo=SimpleUploadedFile("p.jpg", make_image_bytes(fmt="JPEG", size=(900, 100))))
    html = html_of(client)
    assert html.count("aspect-square") == 2


# --- order ---------------------------------------------------------------------------------------


def test_available_products_come_first_then_alphabetical(client, product_fields):
    make(product_fields, trade_name="c")
    make(product_fields, trade_name="a", is_available=False)
    make(product_fields, trade_name="b")
    make(product_fields, trade_name="d", is_available=False)
    assert names(get(client)) == ["b", "c", "a", "d"]


def test_search_ranking_wins_over_the_default_order_and_keeps_it_inside_a_rank(client, product_fields):
    by_usage = make(product_fields, trade_name="a", usage=SCORE)
    make(product_fields, trade_name="c " + SCORE, is_available=False)
    make(product_fields, trade_name="b " + SCORE)
    assert names(get(client, q=SCORE)) == ["b " + SCORE, "c " + SCORE, by_usage.trade_name]


# --- the type filter -------------------------------------------------------------------------------


def test_the_chips_are_all_plus_the_types_that_have_products(client, product_fields):
    make(product_fields)
    other_type()  # a type nobody uses is not offered
    assert chips(html_of(client)) == [("\u0647\u0645\u0647", True), (product_fields["product_type"].name, False)]


def test_chips_follow_the_types_own_order(client, product_fields):
    late = ProductType.objects.create(name="\u0627", order=5)
    early = ProductType.objects.create(name="\u0632", order=1)
    make(product_fields, product_type=late, trade_name="x")
    make(product_fields, product_type=early, trade_name="y")
    assert [n for n, _ in chips(html_of(client))][1:] == [early.name, late.name]


def test_the_chosen_type_narrows_the_list_and_is_marked_current(client, product_fields):
    mine = make(product_fields, trade_name="a")
    other = other_type()
    make({**product_fields, "product_type": other}, trade_name="b")
    response = get(client, type=mine.product_type.slug)
    assert names(response) == ["a"]
    assert dict(chips(response.content.decode())) == {"\u0647\u0645\u0647": False, mine.product_type.name: True, other.name: False}


def test_an_unknown_type_is_ignored_not_a_404(client, product_fields):
    make(product_fields, trade_name="a")
    response = get(client, type="no-such-type")
    assert names(response) == ["a"]
    assert chips(response.content.decode())[0] == ("\u0647\u0645\u0647", True)


def test_a_type_with_no_products_is_ignored_too(client, product_fields):
    make(product_fields, trade_name="a")
    empty = other_type()
    assert names(get(client, type=empty.slug)) == ["a"]


def test_the_type_name_itself_is_not_searched(client, product_fields):
    make(product_fields)
    html = html_of(client, q=product_fields["product_type"].name)
    assert 'id="empty"' in html


def test_chips_keep_the_search_text_and_the_form_keeps_the_type(client, product_fields):
    product = make(product_fields, trade_name=SCORE)
    html = html_of(client, q=SCORE, type=product.product_type.slug)
    nav = re.search(r"<nav[^>]*>(.*?)</nav>", html, re.S).group(1)
    assert nav.count(urlencode({"q": SCORE})) == 2  # on both chips
    hrefs = re.findall(r'<a href="([^"]*)"', nav)
    assert "type=" not in hrefs[0]  # "all" drops the type
    assert urlencode({"type": product.product_type.slug}) in hrefs[1]
    form = re.search(r"<form.*?</form>", html, re.S).group(0)
    assert f'<input type="hidden" name="type" value="{product.product_type.slug}">' in form
    assert f'value="{SCORE}"' in form


def test_the_form_has_no_hidden_type_when_none_is_chosen(client, product_fields):
    make(product_fields)
    form = re.search(r"<form.*?</form>", html_of(client), re.S).group(0)
    assert 'type="hidden"' not in form


# --- search --------------------------------------------------------------------------------------


def test_the_search_box_uses_the_persian_aware_search(client, product_fields):
    make(product_fields, trade_name=SCORE)
    make(product_fields, trade_name="other")
    assert names(get(client, q=SCORE_ARABIC_KAF)) == [SCORE]


def test_the_search_finds_by_crop_and_pest(client, product_fields, crop, pest):
    by_crop = make(product_fields, trade_name="a")
    by_crop.crops.add(crop)
    by_pest = make(product_fields, trade_name="b")
    by_pest.pests.add(pest)
    make(product_fields, trade_name="c")
    assert names(get(client, q=crop.name)) == ["a"]
    assert names(get(client, q=pest.name)) == ["b"]


def test_search_and_type_work_together(client, product_fields):
    mine = make(product_fields, trade_name=SCORE)
    make({**product_fields, "product_type": other_type()}, trade_name=SCORE + " 2")
    assert names(get(client, q=SCORE, type=mine.product_type.slug)) == [SCORE]


def test_search_keeps_unavailable_products(client, product_fields):
    make(product_fields, trade_name=SCORE, is_available=False)
    assert names(get(client, q=SCORE)) == [SCORE]


def test_a_blank_search_shows_everything(client, product_fields):
    make(product_fields, trade_name="a")
    make(product_fields, trade_name="b")
    assert names(get(client, q="   ")) == ["a", "b"]


def test_a_very_long_search_is_cut_not_refused(client, product_fields):
    make(product_fields, trade_name="a")
    response = get(client, q="x" * 5000)
    assert len(response.context["q"]) == MAX_QUERY_LENGTH
    html = response.content.decode()
    assert "x" * (MAX_QUERY_LENGTH + 1) not in html


def test_the_search_text_is_escaped_on_the_page(client, product_fields):
    make(product_fields)
    html = html_of(client, q='"><script>alert(1)</script>')
    assert "<script>alert(1)</script>" not in html


def test_the_count_is_shown_in_persian_digits(client, product_fields):
    for i in range(12):
        make(product_fields, trade_name=f"p{i}")
    assert "\u06f1\u06f2 \u0645\u062d\u0635\u0648\u0644" in html_of(client)  # ۱۲ محصول


# --- when nothing matches --------------------------------------------------------------------------


def test_nothing_found_says_so_and_offers_the_call_button(client, product_fields):
    make(product_fields)
    html = html_of(client, q="\u0646\u0627\u06cc\u0627\u0628\u06cc\u0627\u0628")
    empty = re.search(r'<section id="empty".*?</section>', html, re.S).group(0)
    assert "\u0645\u062d\u0635\u0648\u0644\u06cc \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f" in empty  # محصولی پیدا نشد
    assert TEL in empty
    assert "0911 274 7628" in empty
    button = re.search(rf"<a {re.escape(TEL)} class=\"([^\"]*)\"", empty)
    assert button and "hidden" not in button.group(1).split()  # visible on phones too
    assert f'href="{URL}"' in empty  # show everything again
    assert "<ul" not in html


def test_an_empty_catalog_has_its_own_message_and_still_the_call_button(client):
    html = html_of(client)
    empty = re.search(r'<section id="empty".*?</section>', html, re.S).group(0)
    assert "\u0647\u0646\u0648\u0632 \u0645\u062d\u0635\u0648\u0644\u06cc \u062b\u0628\u062a \u0646\u0634\u062f\u0647" in empty  # هنوز محصولی ثبت نشده
    assert TEL in empty
    assert f'href="{URL}"' not in empty  # nothing to go back to


def test_no_empty_state_when_there_are_results(client, product_fields):
    make(product_fields)
    assert 'id="empty"' not in html_of(client)


# --- queries ---------------------------------------------------------------------------------------


def count_queries(client, **params):
    with CaptureQueriesContext(connection) as queries:
        get(client, **params)
    return len(queries)


def test_the_number_of_queries_does_not_depend_on_the_number_of_products(client, product_fields, crop, pest):
    for i in range(3):
        product = make(product_fields, trade_name=f"p{i}", photo=SimpleUploadedFile("p.jpg", make_image_bytes(fmt="JPEG", size=(50, 50))))
        product.crops.add(crop)
        product.pests.add(pest)
    client.get(URL)  # the site settings row is created on the first request
    few = count_queries(client)
    few_search = count_queries(client, q="p")
    for i in range(3, 30):
        other = make({**product_fields, "product_type": other_type(f"t{i}")}, trade_name=f"p{i}")
        other.crops.add(crop)
        other.pests.add(pest)
    assert Product.objects.count() == 30
    assert count_queries(client) == few
    assert count_queries(client, q="p") == few_search


def test_a_page_costs_a_handful_of_queries(client, product_fields):
    make(product_fields)
    client.get(URL)
    # site settings, types, products, crops, pests
    assert count_queries(client) <= 6
