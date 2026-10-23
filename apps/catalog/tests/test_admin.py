import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Crop, Pest, ProductType

pytestmark = pytest.mark.django_db

ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
ZWNJ = "\u200c"
KOLZA = PERSIAN_KAF + "\u0644\u0632\u0627"  # کلزا
KOLZA_ARABIC = ARABIC_KAF + "\u0644\u0632\u0627"
WHEAT = "\u06af\u0646\u062f\u0645"  # گندم
WITH_ZWNJ = "\u0633\u0627\u0642\u0647" + ZWNJ + "\u062e\u0648\u0627\u0631"  # ساقه‌خوار
WITHOUT_ZWNJ = "\u0633\u0627\u0642\u0647\u062e\u0648\u0627\u0631"
PLUM = "\u0622\u0644\u0648"  # آلو
PLUM_NO_MADDA = "\u0627\u0644\u0648"  # الو

MODELS = {"producttype": ProductType, "crop": Crop, "pest": Pest}
TAG_NAMES = ["crop", "pest"]


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


def url(kind, view, *args):
    return reverse(f"admin:catalog_{kind}_{view}", args=args)


def found(client, kind, query):
    response = client.get(url(kind, "changelist"), {"q": query})
    assert response.status_code == 200
    return {item.name for item in response.context["cl"].result_list}


@pytest.mark.parametrize("kind", MODELS)
def test_changelist_opens(admin_client, kind):
    assert admin_client.get(url(kind, "changelist")).status_code == 200


@pytest.mark.parametrize("kind", MODELS)
def test_staff_without_permission_is_refused(staff_client, kind):
    assert staff_client.get(url(kind, "changelist")).status_code == 403
    assert staff_client.get(url(kind, "add")).status_code == 403


@pytest.mark.parametrize("kind", MODELS)
def test_adding_through_the_admin_creates_a_row_with_a_slug(admin_client, kind):
    data = {"name": KOLZA_ARABIC}
    if kind == "producttype":
        data["order"] = 3
    response = admin_client.post(url(kind, "add"), data)
    assert response.status_code == 302
    item = MODELS[kind].objects.get()
    assert item.name == KOLZA
    assert item.slug == KOLZA


@pytest.mark.parametrize("kind", MODELS)
def test_a_duplicate_is_rejected_with_a_readable_message(admin_client, kind):
    MODELS[kind].objects.create(name=WITH_ZWNJ)
    data = {"name": WITHOUT_ZWNJ}
    if kind == "producttype":
        data["order"] = 0
    response = admin_client.post(url(kind, "add"), data)
    assert response.status_code == 200  # the form is shown again with the error
    assert MODELS[kind].objects.count() == 1
    assert "از قبل ثبت شده است" in response.content.decode()


@pytest.mark.parametrize("kind", MODELS)
def test_slug_is_shown_read_only_and_only_once_it_exists(admin_client, kind):
    add = admin_client.get(url(kind, "add")).content.decode()
    assert "field-slug" not in add  # nothing to show for a new row
    item = MODELS[kind].objects.create(name=WHEAT)
    change = admin_client.get(url(kind, "change", item.pk)).content.decode()
    assert "field-slug" in change
    assert 'name="slug"' not in change  # shown, but not an input


def test_the_name_key_is_not_on_the_form(admin_client):
    crop = Crop.objects.create(name=WHEAT)
    html = admin_client.get(url("crop", "change", crop.pk)).content.decode()
    assert "name_key" not in html


@pytest.mark.parametrize("kind", TAG_NAMES)
def test_alternate_names_can_be_saved_and_are_listed(admin_client, kind):
    response = admin_client.post(
        url(kind, "add"),
        {"name": WHEAT, "alternate_names": "wheat\n\n  Wheat\n"},
    )
    assert response.status_code == 302
    assert MODELS[kind].objects.get().alternate_names == "wheat"
    listing = admin_client.get(url(kind, "changelist")).content.decode()
    assert "wheat" in listing


def test_product_types_can_be_reordered_from_the_list(admin_client):
    a = ProductType.objects.create(name="\u0627", order=1)
    b = ProductType.objects.create(name="\u0628", order=2)
    response = admin_client.post(
        url("producttype", "changelist"),
        {
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "2",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": a.pk,
            "form-0-order": "5",
            "form-1-id": b.pk,
            "form-1-order": "2",
            "_save": "Save",
        },
    )
    assert response.status_code == 302
    a.refresh_from_db()
    assert a.order == 5
    assert list(ProductType.objects.all()) == [b, a]


# --- search ------------------------------------------------------------------


@pytest.mark.parametrize("kind", MODELS)
def test_search_ignores_which_kaf_was_typed(admin_client, kind):
    MODELS[kind].objects.create(name=KOLZA)
    MODELS[kind].objects.create(name=WHEAT)
    assert found(admin_client, kind, KOLZA_ARABIC) == {KOLZA}


@pytest.mark.parametrize("kind", MODELS)
def test_search_ignores_the_half_space(admin_client, kind):
    MODELS[kind].objects.create(name=WITH_ZWNJ)
    MODELS[kind].objects.create(name=WHEAT)
    assert found(admin_client, kind, WITHOUT_ZWNJ) == {WITH_ZWNJ}


@pytest.mark.parametrize("kind", MODELS)
def test_search_finds_alef_with_madda_when_typed_without_it(admin_client, kind):
    MODELS[kind].objects.create(name=PLUM)
    MODELS[kind].objects.create(name=WHEAT)
    assert found(admin_client, kind, PLUM_NO_MADDA) == {PLUM}


@pytest.mark.parametrize("kind", MODELS)
def test_search_needs_every_word_to_match(admin_client, kind):
    both = "\u06a9\u0631\u0645 " + WITH_ZWNJ  # کرم ساقه‌خوار
    MODELS[kind].objects.create(name=both)
    MODELS[kind].objects.create(name="\u06a9\u0631\u0645 \u0628\u0631\u06af")  # کرم برگ
    assert found(admin_client, kind, "\u06a9\u0631\u0645") == {both, "\u06a9\u0631\u0645 \u0628\u0631\u06af"}
    assert found(admin_client, kind, "\u06a9\u0631\u0645 " + WITHOUT_ZWNJ) == {both}


@pytest.mark.parametrize("kind", TAG_NAMES)
def test_search_also_looks_in_alternate_names(admin_client, kind):
    MODELS[kind].objects.create(name=WHEAT, alternate_names="Wheat grain")
    MODELS[kind].objects.create(name=KOLZA)
    assert found(admin_client, kind, "wheat") == {WHEAT}


@pytest.mark.parametrize("kind", MODELS)
def test_empty_and_invisible_searches_show_everything(admin_client, kind):
    MODELS[kind].objects.create(name=KOLZA)
    MODELS[kind].objects.create(name=WHEAT)
    assert found(admin_client, kind, "") == {KOLZA, WHEAT}
    assert found(admin_client, kind, ZWNJ) == {KOLZA, WHEAT}
