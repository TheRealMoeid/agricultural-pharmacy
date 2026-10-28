"""Tests for Article.

Look-alike characters (Arabic and Persian kaf) are written as escapes, as in
the other test files.
"""
import datetime
import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image

from apps.articles.models import Article

from .conftest import make_image_bytes

pytestmark = pytest.mark.django_db

Season = Article.Season
ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
REQUIRED = "این فیلد را پر کنید."
TITLE = "\u0645\u0642\u0627\u0644\u0647 \u0622\u0632\u0645\u0627\u06cc\u0634\u06cc"  # مقاله آزمایشی


def data(**overrides):
    base = {"title": TITLE, "season": Season.SPRING, "body": "\u0645\u062a\u0646"}
    return {**base, **overrides}


def make(**overrides):
    return Article.objects.create(**data(**overrides))


def upload(size=(2400, 1200)):
    return SimpleUploadedFile("IMG_1.jpg", make_image_bytes(fmt="JPEG", size=size))


# --- defaults and identity -----------------------------------------------------------


def test_str_is_the_title():
    assert str(make()) == TITLE


def test_a_new_article_is_a_draft_without_a_date():
    article = make()
    assert article.is_published is False
    assert article.published_date is None
    assert not article.cover_image


def test_the_four_seasons_are_stored_as_these_values():
    assert Season.values == ["spring", "summer", "autumn", "winter"]
    assert [label for _, label in Season.choices] == ["بهار", "تابستان", "پاییز", "زمستان"]


def test_a_season_that_does_not_exist_is_refused():
    with pytest.raises(ValidationError) as exc:
        Article(**data(season="monsoon")).full_clean()
    assert "season" in exc.value.message_dict


def test_the_season_is_required():
    with pytest.raises(ValidationError) as exc:
        Article(**data(season="")).full_clean()
    assert "season" in exc.value.message_dict


# --- title and body ----------------------------------------------------------------------


@pytest.mark.parametrize("missing", ["title", "body"])
def test_title_and_body_are_required(missing):
    with pytest.raises(ValidationError) as exc:
        Article(**data(**{missing: ""})).full_clean()
    assert list(exc.value.message_dict) == [missing]


@pytest.mark.parametrize("field", ["title", "body"])
def test_text_of_only_spaces_is_refused_once_with_our_message(field):
    with pytest.raises(ValidationError) as exc:
        Article(**data(**{field: " \n  "})).full_clean()
    assert exc.value.message_dict[field] == [REQUIRED]


def test_a_title_that_grows_when_cleaned_is_refused_instead_of_crashing():
    # U+FDFA is one character that NFKC turns into eighteen: twelve of them fit
    # in the 200-character title as typed (12), but not once cleaned (216).
    with pytest.raises(ValidationError) as exc:
        Article(**data(title="\ufdfa" * 12)).full_clean()
    assert "title" in exc.value.message_dict


def test_the_title_is_cleaned_when_saved():
    article = make(title="  " + ARABIC_KAF + "\u0627\u0631   \u06af\u0646\u062f\u0645 ")
    article.refresh_from_db()
    assert article.title == PERSIAN_KAF + "\u0627\u0631 \u06af\u0646\u062f\u0645"


def test_the_body_keeps_its_paragraphs_but_unifies_letters_and_trims():
    article = make(body="\n  " + ARABIC_KAF + "\u0627\u0631\n\n\u062f\u0648\u0645  \n")
    article.refresh_from_db()
    assert article.body == PERSIAN_KAF + "\u0627\u0631\n\n\u062f\u0648\u0645"


# --- slug --------------------------------------------------------------------------------


def test_slug_is_made_from_the_title_once():
    article = make(title="\u0645\u0642\u0627\u0644\u0647 \u0628\u0647\u0627\u0631")
    assert article.slug == "\u0645\u0642\u0627\u0644\u0647-\u0628\u0647\u0627\u0631"
    article.title = "\u0639\u0646\u0648\u0627\u0646 \u062f\u06cc\u06af\u0631"
    article.save()
    article.refresh_from_db()
    assert article.slug == "\u0645\u0642\u0627\u0644\u0647-\u0628\u0647\u0627\u0631"


def test_slug_collisions_are_numbered():
    first = make(title="x")
    second = make(title="x")
    third = make(title="x")
    assert [first.slug, second.slug, third.slug] == ["x", "x-2", "x-3"]


def test_a_title_with_no_letters_still_gets_a_slug():
    assert make(title="!!!").slug == "article"


def test_an_explicit_slug_is_kept():
    assert make(slug="spring-tips").slug == "spring-tips"


# --- publishing ----------------------------------------------------------------------------


def test_publishing_without_a_date_uses_todays_date_in_the_store_time_zone(monkeypatch):
    # 21:00 UTC on 20 March is already 21 March in Tehran (UTC+3:30).
    fake_now = datetime.datetime(2026, 3, 20, 21, 0, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(timezone, "now", lambda: fake_now)
    article = make(is_published=True)
    assert article.published_date == datetime.date(2026, 3, 21)


def test_a_date_that_was_given_is_kept():
    article = make(is_published=True, published_date=datetime.date(2026, 1, 5))
    assert article.published_date == datetime.date(2026, 1, 5)


def test_full_clean_fills_the_date_too():
    article = Article(**data(is_published=True))
    article.full_clean()
    assert article.published_date is not None


def test_a_draft_may_carry_a_planned_date():
    article = make(published_date=datetime.date(2026, 9, 1))
    assert article.is_published is False
    assert article.published_date == datetime.date(2026, 9, 1)


def test_the_database_refuses_a_published_article_without_a_date():
    with pytest.raises(IntegrityError), transaction.atomic():
        Article.objects.bulk_create([Article(**data(slug="a", is_published=True))])


def test_published_lists_only_published_articles_newest_first():
    old = make(title="old", is_published=True, published_date=datetime.date(2026, 1, 1))
    draft = make(title="draft")
    new = make(title="new", is_published=True, published_date=datetime.date(2026, 6, 1))
    same_day_later = make(title="later", is_published=True, published_date=datetime.date(2026, 6, 1))
    assert list(Article.objects.published()) == [same_day_later, new, old]
    assert draft not in Article.objects.published()


def test_the_section_is_empty_until_the_first_article_is_published():
    make()
    assert not Article.objects.published().exists()
    make(title="live", is_published=True)
    assert Article.objects.published().exists()


def test_the_default_order_is_newest_created_first():
    first = make(title="a")
    second = make(title="b")
    assert list(Article.objects.all()) == [second, first]


# --- cover image -----------------------------------------------------------------------------


def test_the_cover_image_settings_are_those_of_product_photos():
    field = Article._meta.get_field("cover_image")
    assert (field.max_side, field.quality, field.max_bytes) == (800, 80, 50_000)
    assert (field.thumb_side, field.thumb_max_bytes) == (320, 12_000)


def test_a_cover_image_is_stored_as_a_webp_and_a_thumbnail_in_articles(media_root):
    article = make(cover_image=upload())
    article.refresh_from_db()
    assert article.cover_image.name.startswith("articles/")
    assert article.cover_image.name.endswith(".webp")
    with article.cover_image.open("rb") as f:
        image = Image.open(io.BytesIO(f.read()))
    assert image.format == "WEBP"
    assert image.size == (800, 400)
    assert len(list((media_root / "articles").iterdir())) == 2
    assert article.cover_image.thumb_url.endswith("_thumb.webp")


def test_a_non_image_cover_is_refused_with_a_message_on_the_field():
    bad = SimpleUploadedFile("a.jpg", b"not an image")
    with pytest.raises(ValidationError) as exc:
        Article(**data(cover_image=bad)).full_clean()
    assert "تصویر معتبری نیست" in exc.value.message_dict["cover_image"][0]


# --- migrations ---------------------------------------------------------------------------------


def test_migrations_are_in_sync_with_the_models():
    call_command("makemigrations", "articles", "--check", "--dry-run")
