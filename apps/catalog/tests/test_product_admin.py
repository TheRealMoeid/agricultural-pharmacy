import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Product

from .conftest import make_image_bytes

pytestmark = pytest.mark.django_db

ARABIC_KAF = "\u0643"


@pytest.fixture
def admin_client():
    user = get_user_model().objects.create_superuser("boss", "boss@example.com", "pw-for-tests-123")
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def staff_client():
    user = get_user_model().objects.create_user("helper", password="pw-for-tests-123", is_staff=True)
    client = Client()
    client.force_login(user)
    return client


def url(view, *args):
    return reverse(f"admin:catalog_product_{view}", args=args)


def test_changelist_opens(admin_client):
    assert admin_client.get(url("changelist")).status_code == 200


def test_staff_without_permission_is_refused(staff_client):
    assert staff_client.get(url("changelist")).status_code == 403


def test_adding_a_product_through_the_admin(admin_client, product_fields):
    data = {k: (v.pk if k == "product_type" else v) for k, v in product_fields.items()}
    data.update(
        usage="",
        dosage="",
        timing="",
        production_date="",
        expiry_date="",
        crops=[],
        pests=[],
    )
    response = admin_client.post(url("add"), data)
    assert response.status_code == 302, response.context["adminform"].form.errors if response.status_code == 200 else None
    product = Product.objects.get()
    assert product.trade_name == product_fields["trade_name"]


def test_the_is_available_checkbox_is_honoured(admin_client, product_fields):
    data = {k: (v.pk if k == "product_type" else v) for k, v in product_fields.items()}
    data.update(usage="", dosage="", timing="", production_date="", expiry_date="", crops=[], pests=[])
    # No "is_available" key at all: an admin checkbox left unticked is simply
    # absent from the POST, and Django reads that as False.
    admin_client.post(url("add"), data)
    assert Product.objects.get().is_available is False


def test_slug_is_shown_read_only_and_only_once_it_exists(admin_client, product_fields):
    add = admin_client.get(url("add")).content.decode()
    assert "field-slug" not in add
    product = Product.objects.create(**product_fields)
    change = admin_client.get(url("change", product.pk)).content.decode()
    assert "field-slug" in change
    assert 'name="slug"' not in change


def test_a_product_type_in_use_cannot_be_deleted_from_its_own_admin(admin_client, product_fields):
    product = Product.objects.create(**product_fields)
    response = admin_client.post(
        reverse("admin:catalog_producttype_delete", args=[product.product_type.pk]), {"post": "yes"}
    )
    assert response.status_code == 200  # Django shows the "protected" page instead of deleting
    product.refresh_from_db()
    assert product.product_type_id is not None


def test_crops_and_pests_can_be_set_from_the_admin(admin_client, product_fields, crop, pest):
    data = {k: (v.pk if k == "product_type" else v) for k, v in product_fields.items()}
    data.update(
        usage="",
        dosage="",
        timing="",
        production_date="",
        expiry_date="",
        crops=[crop.pk],
        pests=[pest.pk],
        is_available="on",
    )
    response = admin_client.post(url("add"), data)
    assert response.status_code == 302
    product = Product.objects.get()
    assert list(product.crops.all()) == [crop]
    assert list(product.pests.all()) == [pest]


def test_an_uploaded_photo_is_stored(admin_client, product_fields):
    upload = SimpleUploadedFile("leaf.png", make_image_bytes(), content_type="image/png")
    data = {k: (v.pk if k == "product_type" else v) for k, v in product_fields.items()}
    data.update(usage="", dosage="", timing="", production_date="", expiry_date="", crops=[], pests=[])
    response = admin_client.post(url("add"), {**data, "photo": upload})
    assert response.status_code == 302
    product = Product.objects.get()
    assert product.photo.name.startswith("products/")
    assert product.photo.name.endswith(".webp")


def test_a_corrupt_file_disguised_as_an_image_is_rejected(admin_client, product_fields):
    # A real image is validated at the form level by Django's own
    # forms.ImageField (which the admin uses), on top of the model validator
    # that only checks the extension. This is what actually stops a renamed
    # non-image file.
    upload = SimpleUploadedFile("leaf.png", b"not actually an image", content_type="image/png")
    data = {k: (v.pk if k == "product_type" else v) for k, v in product_fields.items()}
    data.update(usage="", dosage="", timing="", production_date="", expiry_date="", crops=[], pests=[])
    response = admin_client.post(url("add"), {**data, "photo": upload})
    assert response.status_code == 200
    assert Product.objects.count() == 0


def test_availability_filter_is_offered_in_the_sidebar(admin_client, product_fields):
    Product.objects.create(**product_fields)
    html = admin_client.get(url("changelist")).content.decode()
    assert "موجود است" in html
    assert "is_available__exact=1" in html


def test_crops_and_pests_use_the_dual_list_widget(admin_client, product_fields):
    product = Product.objects.create(**product_fields)
    html = admin_client.get(url("change", product.pk)).content.decode()
    # A plain multi-select would not carry this class; only the horizontal
    # filter widget (FilteredSelectMultiple) adds it, and the admin's own JS
    # uses it to build the dual-list UI at runtime.
    assert html.count('class="selectfilter"') == 2  # crops and pests


def test_list_filter_by_type_and_availability(admin_client, product_fields, product_type):
    Product.objects.create(**product_fields)
    unavailable = {**product_fields, "trade_name": "\u062f\u06cc\u06af\u0631", "is_available": False}
    Product.objects.create(**unavailable)
    response = admin_client.get(url("changelist"), {"is_available__exact": "1"})
    assert response.status_code == 200
    names = {p.trade_name for p in response.context["cl"].result_list}
    assert names == {product_fields["trade_name"]}


def test_search_box_finds_by_trade_and_generic_name(admin_client, product_fields):
    Product.objects.create(**product_fields)
    other = {**product_fields, "trade_name": "\u062f\u06cc\u06af\u0631", "generic_name": "\u0686\u06cc\u0632 \u062f\u06cc\u06af\u0631"}
    Product.objects.create(**other)
    response = admin_client.get(url("changelist"), {"q": product_fields["generic_name"]})
    names = {p.trade_name for p in response.context["cl"].result_list}
    assert names == {product_fields["trade_name"]}


def _photo_post(product_fields, photo):
    data = {k: (v.pk if k == "product_type" else v) for k, v in product_fields.items()}
    data.update(usage="", dosage="", timing="", production_date="", expiry_date="", crops=[], pests=[])
    return {**data, "photo": photo}


def test_a_large_phone_photo_uploaded_in_the_admin_is_shrunk(admin_client, product_fields):
    from PIL import Image

    big = SimpleUploadedFile("IMG_1.jpg", make_image_bytes(fmt="JPEG", size=(3000, 2000)), content_type="image/jpeg")
    response = admin_client.post(url("add"), _photo_post(product_fields, big))
    assert response.status_code == 302
    product = Product.objects.get()
    with product.photo.open("rb") as f:
        image = Image.open(f)
        assert image.format == "WEBP"
        assert image.size == (800, 533)


def test_a_non_image_in_the_admin_shows_the_message_next_to_the_form(admin_client, product_fields):
    bad = SimpleUploadedFile("notes.jpg", b"just some text", content_type="image/jpeg")
    response = admin_client.post(url("add"), _photo_post(product_fields, bad))
    assert response.status_code == 200
    assert Product.objects.count() == 0
    assert "errorlist" in response.content.decode()


def test_a_gif_in_the_admin_is_refused_with_the_format_message(admin_client, product_fields):
    gif = SimpleUploadedFile("a.gif", make_image_bytes(fmt="GIF"), content_type="image/gif")
    response = admin_client.post(url("add"), _photo_post(product_fields, gif))
    assert response.status_code == 200
    assert Product.objects.count() == 0
    assert "فقط تصویر jpg" in response.content.decode()


def test_editing_a_product_without_touching_the_photo_keeps_it(admin_client, product_fields):
    admin_client.post(url("add"), _photo_post(product_fields, SimpleUploadedFile("a.jpg", make_image_bytes())))
    product = Product.objects.get()
    name = product.photo.name
    data = _photo_post(product_fields, "")
    del data["photo"]
    data["trade_name"] = product_fields["trade_name"] + " ۲"
    response = admin_client.post(url("change", product.pk), data)
    assert response.status_code == 302
    product.refresh_from_db()
    assert product.photo.name == name
