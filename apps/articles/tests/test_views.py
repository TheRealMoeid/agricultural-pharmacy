"""Tests for the public articles pages (D46) and the header link that depends on them (D11).

As in the other tests, anything that could look like another letter is written
as an escape.
"""
import datetime
import re
from urllib.parse import quote, unquote

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.template import RequestContext, Template
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.articles.models import Article
from apps.articles.views import split_paragraphs

from .conftest import make_image_bytes

pytestmark = pytest.mark.django_db

Season = Article.Season
LIST = "/articles/"
ALL = "\u0647\u0645\u0647"  # همه
DAY = datetime.date(2026, 3, 21)  # 1 Farvardin 1405
DAY_FA = "\u06f1\u06f4\u06f0\u06f5/\u06f0\u06f1/\u06f0\u06f1"  # ۱۴۰۵/۰۱/۰۱
NOT_FOUND_HEADING = "\u0627\u06cc\u0646 \u0645\u0642\u0627\u0644\u0647 \u062f\u0631 \u062f\u0633\u062a\u0631\u0633 \u0646\u06cc\u0633\u062a"  # این مقاله در دسترس نیست
EMPTY_HEADING = "\u0647\u0646\u0648\u0632 \u0645\u0642\u0627\u0644\u0647\u200c\u0627\u06cc \u0645\u0646\u062a\u0634\u0631 \u0646\u0634\u062f\u0647 \u0627\u0633\u062a"  # هنوز مقاله‌ای منتشر نشده است
MENU_LABEL = "\u0645\u0642\u0627\u0644\u0627\u062a"  # مقالات


def make(title, season=Season.SPRING, published=True, date=DAY, body="body", **extra):
    return Article.objects.create(
        title=title,
        season=season,
        body=body,
        is_published=published,
        published_date=date if published else None,
        **extra,
    )


def call_href(path):
    """The tracked call button's href for a page at `path` (same helper idea as the product tests)."""
    return f'href="/click/call/?from={quote(unquote(path))}"'


def html_of(client, url, **params):
    response = client.get(url, params)
    assert response.status_code == 200
    return response.content.decode()


def titles(response):
    return [a.title for a in response.context["articles"]]


def chips(html):
    nav = re.search(r"<nav[^>]*>(.*?)</nav>", html, re.S).group(1)
    return [
        (name, 'aria-current="true"' in attrs)
        for attrs, name in re.findall(r"<a href=\"[^\"]*\"([^>]*)>(.*?)</a>", nav, re.S)
    ]


def photo(size=(1200, 900)):
    return SimpleUploadedFile("c.jpg", make_image_bytes(fmt="JPEG", size=size))


# --- addresses --------------------------------------------------------------------------------


def test_the_addresses():
    assert reverse("articles:article_list") == LIST
    assert reverse("articles:article_detail", args=["x"]) == "/articles/x/"


# --- the list ---------------------------------------------------------------------------------


def test_only_published_articles_are_listed_newest_first(client):
    make("old", date=datetime.date(2026, 1, 1))
    make("draft", published=False)
    make("new", date=datetime.date(2026, 6, 1))
    response = client.get(LIST)
    assert response.status_code == 200
    assert titles(response) == ["new", "old"]
    assert "draft" not in response.content.decode()


def test_the_page_heading_and_language(client):
    make("a")
    html = html_of(client, LIST)
    assert '<html lang="fa" dir="rtl"' in html
    assert re.findall(r"<h1[^>]*>(.*?)</h1>", html) == [MENU_LABEL]


def test_a_card_links_to_the_article_and_shows_season_and_jalali_date(client):
    article = make("a", season=Season.AUTUMN)
    html = html_of(client, LIST)
    assert f'href="{reverse("articles:article_detail", args=[article.slug])}"' in html
    assert Season.AUTUMN.label in html
    assert DAY_FA in html
    assert "2026-03-21" not in html


def test_the_card_uses_the_thumbnail_not_the_main_cover(client):
    article = make("a", cover_image=photo())
    html = html_of(client, LIST)
    img = re.search(r"<img [^>]*>", html).group(0)
    assert f'src="{article.cover_image.thumb_url}"' in img
    assert 'loading="lazy"' in img
    assert article.cover_image.url not in html.replace(article.cover_image.thumb_url, "")


def test_an_article_without_a_cover_has_no_image_and_no_error(client):
    make("a")
    assert "<img" not in html_of(client, LIST)


def test_the_list_has_no_empty_state_when_there_are_articles(client):
    make("a")
    assert 'id="empty"' not in html_of(client, LIST)


def test_with_nothing_published_the_list_says_so_and_offers_the_call_button(client):
    make("draft", published=False)
    html = html_of(client, LIST)
    section = re.search(r'<section id="empty".*?</section>', html, re.S).group(0)
    assert EMPTY_HEADING in section
    assert call_href(LIST) in section
    assert "<ul" not in html


# --- seasons ----------------------------------------------------------------------------------


def test_season_chips_are_all_plus_the_seasons_that_have_published_articles_in_season_order(client):
    make("s", season=Season.SUMMER)
    make("p", season=Season.SPRING)
    make("w", season=Season.WINTER, published=False)  # only a draft: not offered
    assert chips(html_of(client, LIST)) == [
        (ALL, True),
        (Season.SPRING.label, False),
        (Season.SUMMER.label, False),
    ]


def test_no_chips_when_only_one_season_has_articles(client):
    make("a")
    make("b")
    assert "<nav" not in html_of(client, LIST)


def test_a_season_narrows_the_list_and_is_marked_current(client):
    make("spring-one", season=Season.SPRING)
    make("summer-one", season=Season.SUMMER)
    response = client.get(LIST, {"season": "summer"})
    assert titles(response) == ["summer-one"]
    assert dict(chips(response.content.decode())) == {ALL: False, Season.SPRING.label: False, Season.SUMMER.label: True}


def test_an_unknown_or_unoffered_season_is_ignored_not_a_404(client):
    make("a", season=Season.SPRING)
    make("b", season=Season.SUMMER)
    for value in ("monsoon", "winter", ""):
        response = client.get(LIST, {"season": value})
        assert response.status_code == 200
        assert sorted(titles(response)) == ["a", "b"]
        assert chips(response.content.decode())[0] == (ALL, True)


# --- one article --------------------------------------------------------------------------------


def test_the_page_shows_title_season_date_and_the_paragraphs(client):
    article = make("The title", season=Season.WINTER, body="first\n\nsecond\nline")
    response = client.get(reverse("articles:article_detail", args=[article.slug]))
    html = response.content.decode()
    assert response.status_code == 200
    assert re.findall(r"<h1[^>]*>(.*?)</h1>", html) == ["The title"]
    assert Season.WINTER.label in html
    assert DAY_FA in html
    assert response.context["paragraphs"] == ["first", "second\nline"]
    assert html.count('<p class="mt-4 whitespace-pre-line">') == 2
    assert "<title>The title |" in html


def test_the_body_is_escaped(client):
    article = make("a", body="<script>alert(1)</script>")
    html = html_of(client, reverse("articles:article_detail", args=[article.slug]))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_the_full_cover_is_shown_not_the_thumbnail(client):
    article = make("a", cover_image=photo())
    html = html_of(client, reverse("articles:article_detail", args=[article.slug]))
    img = re.search(r"<img [^>]*>", html).group(0)
    assert f'src="{article.cover_image.url}"' in img
    assert article.cover_image.thumb_url not in img


def test_an_article_without_a_cover_has_no_image(client):
    article = make("a")
    assert "<img" not in html_of(client, reverse("articles:article_detail", args=[article.slug]))


def test_a_persian_slug_is_found(client):
    article = make("\u0645\u0642\u0627\u0644\u0647 \u0628\u0647\u0627\u0631")  # مقاله بهار
    assert article.slug == "\u0645\u0642\u0627\u0644\u0647-\u0628\u0647\u0627\u0631"
    assert client.get(reverse("articles:article_detail", args=[article.slug])).status_code == 200


def test_the_back_link_and_the_ask_an_expert_link(client):
    article = make("a")
    html = html_of(client, reverse("articles:article_detail", args=[article.slug]))
    assert f'<a href="{LIST}" class="font-bold text-brand-700 hover:underline">' in html
    assert f'href="{reverse("consultations:form")}"' in html


@pytest.mark.parametrize("which", ["draft", "missing"])
def test_a_draft_or_missing_article_gets_the_friendly_page_with_a_404(client, which):
    draft = make("hidden", published=False)
    slug = draft.slug if which == "draft" else "no-such-article"
    path = reverse("articles:article_detail", args=[slug])
    response = client.get(path)
    html = response.content.decode()
    assert response.status_code == 404
    assert NOT_FOUND_HEADING in html
    assert html.count(call_href(path)) == 3  # header, call bar and the page's own button
    assert f'href="{LIST}"' in re.search(r"<section.*?</section>", html, re.S).group(0)


# --- the paragraph splitter ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "body, expected",
    [
        ("a\n\nb", ["a", "b"]),
        ("a\n\n\n\nb", ["a", "b"]),
        ("a\n  \nb", ["a", "b"]),
        ("a\r\n\r\nb", ["a", "b"]),
        ("a\nb", ["a\nb"]),
        ("  a  \n\n  b  ", ["a", "b"]),
        ("", []),
        ("   \n\n  ", []),
    ],
)
def test_split_paragraphs(body, expected):
    assert split_paragraphs(body) == expected


# --- the menu link (D11) --------------------------------------------------------------------------


def menu(client, url):
    return re.search(r"<header.*?</header>", html_of(client, url), re.S).group(0)


def test_the_header_has_no_articles_link_until_something_is_published(client):
    assert f'href="{LIST}"' not in menu(client, reverse("pages:contact"))
    make("draft", published=False)
    assert f'href="{LIST}"' not in menu(client, reverse("pages:contact"))


def test_the_header_gets_the_articles_link_once_an_article_is_published(client):
    make("live")
    header = menu(client, reverse("pages:contact"))
    assert f'<a href="{LIST}"' in header and MENU_LABEL in header


def test_the_link_appears_on_every_page_with_the_menu(client):
    make("live")
    for url in (reverse("catalog:product_list"), reverse("pages:experts"), reverse("consultations:form"), LIST):
        assert f'href="{LIST}"' in menu(client, url)


def test_the_home_page_links_to_articles_only_once_something_is_published(client):
    assert f'href="{LIST}"' not in html_of(client, reverse("pages:home"))
    make("live")
    html = html_of(client, reverse("pages:home"))
    assert f'href="{LIST}"' in html
    assert f'href="{LIST}"' not in re.search(r"<header.*?</header>", html, re.S).group(0)  # the menu stays off the home page


# --- the context processor --------------------------------------------------------------------------


def render_flag():
    request = RequestFactory().get("/")
    return Template("{% if has_articles %}yes{% else %}no{% endif %}").render(RequestContext(request))


def test_the_processor_is_registered_and_follows_what_is_published():
    assert render_flag() == "no"
    make("draft", published=False)
    assert render_flag() == "no"
    make("live")
    assert render_flag() == "yes"


def test_the_processor_does_not_query_until_the_value_is_read():
    from apps.articles.context_processors import articles_nav

    with CaptureQueriesContext(connection) as queries:
        value = articles_nav(RequestFactory().get("/"))["has_articles"]
    assert len(queries) == 0
    with CaptureQueriesContext(connection) as queries:
        bool(value)
        bool(value)
    assert len(queries) == 1


# --- self-contained and light -------------------------------------------------------------------------


def test_the_pages_load_nothing_from_other_websites_and_use_only_two_weights(client):
    article = make("a", cover_image=photo())
    for url in (LIST, reverse("articles:article_detail", args=[article.slug])):
        html = html_of(client, url)
        assert not re.search(r'(?:src|href|action)=["\']?(?:https?:)?//', html)
        assert not re.search(r"font-(thin|extralight|light|medium|semibold|extrabold|black)", html)


# --- queries -------------------------------------------------------------------------------------------


def count_queries(client, url):
    with CaptureQueriesContext(connection) as queries:
        assert client.get(url).status_code == 200
    return len(queries)


def test_the_list_costs_a_fixed_number_of_queries(client):
    make("a", season=Season.SPRING)
    client.get(LIST)  # the site settings row is created on the first request
    few = count_queries(client, LIST)
    for i in range(20):
        make(f"n{i}", season=list(Season.values)[i % 4])
    assert count_queries(client, LIST) == few
    assert few == 3  # the site settings, the articles, the menu check


def test_the_article_page_costs_a_fixed_number_of_queries(client):
    article = make("a", body="x\n\ny" * 50)
    url = reverse("articles:article_detail", args=[article.slug])
    client.get(url)
    assert count_queries(client, url) == 3  # the site settings, the article, the menu check
