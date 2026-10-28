import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.articles.models import Article
from apps.core.jalali import jalali_to_gregorian

from .conftest import make_image_bytes

pytestmark = pytest.mark.django_db

TITLE = "\u0645\u0642\u0627\u0644\u0647 \u0622\u0632\u0645\u0627\u06cc\u0634\u06cc"


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


def url(view, *args):
    return reverse(f"admin:articles_article_{view}", args=args)


def post(**overrides):
    return {"title": TITLE, "season": "spring", "body": "\u0645\u062a\u0646", "published_date": "", **overrides}


def test_changelist_opens(admin_client):
    assert admin_client.get(url("changelist")).status_code == 200


def test_staff_without_permission_is_refused(staff_client):
    assert staff_client.get(url("changelist")).status_code == 403
    assert staff_client.get(url("add")).status_code == 403


def test_adding_an_article_makes_a_draft(admin_client):
    response = admin_client.post(url("add"), post())
    assert response.status_code == 302
    article = Article.objects.get()
    assert article.is_published is False
    assert article.slug


def test_publishing_without_a_date_fills_it_in(admin_client):
    response = admin_client.post(url("add"), post(is_published="on"))
    assert response.status_code == 302, getattr(response, "context", None)
    article = Article.objects.get()
    assert article.is_published is True
    assert article.published_date is not None


def test_a_jalali_date_typed_in_the_admin_is_stored_as_gregorian(admin_client):
    admin_client.post(url("add"), post(is_published="on", published_date="1405/01/01"))
    assert Article.objects.get().published_date == jalali_to_gregorian(1405, 1, 1)


def test_an_existing_article_shows_its_date_in_jalali(admin_client):
    article = Article.objects.create(
        title=TITLE, season="spring", body="x", is_published=True,
        published_date=datetime.date(2026, 3, 21),
    )
    html = admin_client.get(url("change", article.pk)).content.decode()
    assert "1405/01/01" in html
    assert "2026-03-21" not in html


def test_a_bad_date_is_refused_with_a_persian_message(admin_client):
    response = admin_client.post(url("add"), post(published_date="not a date"))
    assert response.status_code == 200
    assert Article.objects.count() == 0
    assert "تاریخ را به صورت" in response.content.decode()


def test_the_slug_is_read_only_and_shown_only_once_it_exists(admin_client):
    add = admin_client.get(url("add")).content.decode()
    assert "field-slug" not in add
    article = Article.objects.create(title=TITLE, season="spring", body="x")
    change = admin_client.get(url("change", article.pk)).content.decode()
    assert "field-slug" in change
    assert 'name="slug"' not in change


def test_an_article_can_be_published_with_one_tick_from_the_list(admin_client):
    article = Article.objects.create(title=TITLE, season="spring", body="x")
    response = admin_client.post(
        url("changelist"),
        {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": article.pk,
            "form-0-is_published": "on",
            "_save": "Save",
        },
    )
    assert response.status_code == 302
    article.refresh_from_db()
    assert article.is_published is True
    assert article.published_date is not None  # the list never types a date


def test_the_list_can_be_filtered_by_publication_and_season(admin_client):
    Article.objects.create(title="a", season="spring", body="x")
    html = admin_client.get(url("changelist")).content.decode()
    assert "is_published__exact=1" in html
    assert "season__exact=winter" in html


def test_a_cover_image_uploaded_in_the_admin_is_stored(admin_client):
    photo = SimpleUploadedFile("c.jpg", make_image_bytes(fmt="JPEG", size=(1600, 900)), content_type="image/jpeg")
    response = admin_client.post(url("add"), {**post(), "cover_image": photo})
    assert response.status_code == 302
    assert Article.objects.get().cover_image.name.startswith("articles/")


def test_a_non_image_cover_shows_a_message_next_to_the_form(admin_client):
    bad = SimpleUploadedFile("notes.jpg", b"just text", content_type="image/jpeg")
    response = admin_client.post(url("add"), {**post(), "cover_image": bad})
    assert response.status_code == 200
    assert Article.objects.count() == 0
    assert "errorlist" in response.content.decode()


def test_editing_without_touching_the_cover_keeps_it(admin_client):
    photo = SimpleUploadedFile("c.jpg", make_image_bytes(), content_type="image/jpeg")
    admin_client.post(url("add"), {**post(), "cover_image": photo})
    article = Article.objects.get()
    kept = article.cover_image.name
    response = admin_client.post(url("change", article.pk), post(title=TITLE + " ۲"))
    assert response.status_code == 302
    article.refresh_from_db()
    assert article.cover_image.name == kept
