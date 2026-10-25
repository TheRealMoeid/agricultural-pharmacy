"""Product.photo: what happens to an uploaded photo when the product is saved (D31)."""
import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from PIL import Image, ImageFilter

from apps.catalog.models import Product
from apps.core.images import ImageRejected

from .conftest import make_image_bytes

pytestmark = pytest.mark.django_db


def upload(size=(2400, 1200), fmt="JPEG", name="IMG_2231.jpg"):
    return SimpleUploadedFile(name, make_image_bytes(fmt=fmt, size=size))


def stored_image(product) -> Image.Image:
    with product.photo.open("rb") as f:
        image = Image.open(io.BytesIO(f.read()))
        image.load()
    return image


def test_the_field_settings_are_the_agreed_ones():
    field = Product._meta.get_field("photo")
    assert field.max_side == 800
    assert field.quality == 80
    assert field.max_bytes == 50_000
    assert field.thumb_side == 320
    assert field.thumb_max_bytes == 12_000


def test_the_field_passes_its_own_settings_to_the_conversion(product_fields, monkeypatch):
    field = Product._meta.get_field("photo")
    monkeypatch.setattr(field, "max_side", 100)
    product = Product.objects.create(**product_fields, photo=upload())
    assert stored_image(product).size == (100, 50)


def test_a_saved_photo_is_a_shrunken_webp_in_products(product_fields, media_root):
    product = Product.objects.create(**product_fields, photo=upload())
    product.refresh_from_db()
    assert product.photo.name.startswith("products/")
    assert product.photo.name.endswith(".webp")
    assert "IMG_2231" not in product.photo.name
    image = stored_image(product)
    assert image.format == "WEBP"
    assert image.size == (800, 400)
    main = product.photo.name.split("/")[1]
    stored = sorted(p.name for p in (media_root / "products").iterdir())
    assert stored == sorted([main, main.replace(".webp", "_thumb.webp")])


def test_a_small_thumbnail_is_stored_next_to_the_photo(product_fields, media_root):
    product = Product.objects.create(**product_fields, photo=upload())
    thumb_path = media_root / product.photo.thumb_name
    thumb = Image.open(thumb_path)
    assert thumb.format == "WEBP"
    assert thumb.size == (320, 160)
    assert thumb_path.stat().st_size < (media_root / product.photo.name).stat().st_size
    assert product.photo.thumb_url.endswith("_thumb.webp")
    assert product.photo.thumb_url != product.photo.url


def test_a_field_without_thumbnails_stores_one_file_and_thumb_url_is_the_main_url(
    product_fields, media_root, monkeypatch
):
    monkeypatch.setattr(Product._meta.get_field("photo"), "thumb_side", None)
    product = Product.objects.create(**product_fields, photo=upload())
    assert len(list((media_root / "products").iterdir())) == 1
    assert product.photo.thumb_url == product.photo.url


def test_a_product_without_a_photo_has_no_thumb_url(product_fields):
    product = Product.objects.create(**product_fields)
    with pytest.raises(ValueError):
        product.photo.thumb_url


def test_a_busy_photo_is_held_to_the_size_budgets(product_fields, media_root):
    # Blurred noise: detailed enough that quality 80 would be far over budget.
    busy = Image.effect_noise((900, 700), 60).convert("RGB").filter(ImageFilter.GaussianBlur(1))
    buffer = io.BytesIO()
    busy.save(buffer, format="PNG")
    product = Product.objects.create(**product_fields, photo=SimpleUploadedFile("busy.png", buffer.getvalue()))
    assert (media_root / product.photo.name).stat().st_size <= 50_000
    assert (media_root / product.photo.thumb_name).stat().st_size <= 12_000


def test_if_the_thumbnail_cannot_be_stored_the_main_file_is_removed(product_fields, media_root, monkeypatch):
    storage = Product._meta.get_field("photo").storage
    real_save = storage.save

    def flaky(name, content, *args, **kwargs):
        if name.endswith("_thumb.webp"):
            raise OSError("disk full")
        return real_save(name, content, *args, **kwargs)

    monkeypatch.setattr(storage, "save", flaky)
    with pytest.raises(OSError), transaction.atomic():
        Product.objects.create(**product_fields, photo=upload())
    assert Product.objects.count() == 0
    assert list((media_root / "products").iterdir()) == []


def test_saving_again_does_not_process_the_photo_a_second_time(product_fields):
    product = Product.objects.create(**product_fields, photo=upload())
    first_name = product.photo.name
    product.is_available = False
    product.save()
    product.refresh_from_db()
    assert product.photo.name == first_name


def test_replacing_the_photo_stores_the_new_one(product_fields):
    product = Product.objects.create(**product_fields, photo=upload(size=(2000, 1000)))
    old_name = product.photo.name
    product.photo = upload(size=(600, 900))
    product.save()
    product.refresh_from_db()
    assert product.photo.name != old_name
    assert stored_image(product).size in ((533, 800), (534, 800))


def test_a_product_without_a_photo_is_fine(product_fields):
    product = Product.objects.create(**product_fields)
    product.save()
    assert not product.photo


def test_validation_refuses_a_non_image_with_a_message_on_the_photo_field(product_fields):
    product = Product(**product_fields, photo=SimpleUploadedFile("a.jpg", b"not an image"))
    with pytest.raises(ValidationError) as exc:
        product.full_clean()
    assert "تصویر معتبری نیست" in exc.value.message_dict["photo"][0]


def test_validation_refuses_a_gif(product_fields):
    gif = SimpleUploadedFile("a.gif", make_image_bytes(fmt="GIF"))
    with pytest.raises(ValidationError) as exc:
        Product(**product_fields, photo=gif).full_clean()
    assert "photo" in exc.value.message_dict


def test_validation_passes_for_a_good_photo_and_still_lets_it_be_saved(product_fields):
    product = Product(**product_fields, photo=upload())
    product.full_clean()
    product.save()
    assert stored_image(product).format == "WEBP"


def test_validation_does_not_reopen_a_stored_photo(product_fields, media_root):
    product = Product.objects.create(**product_fields, photo=upload())
    for path in (media_root / "products").iterdir():
        path.write_bytes(b"damaged afterwards")
    product.full_clean()  # would fail if the stored file were read again


def test_a_bad_photo_that_skips_validation_is_still_not_stored(product_fields, media_root):
    with pytest.raises(ImageRejected), transaction.atomic():
        Product.objects.create(**product_fields, photo=SimpleUploadedFile("a.jpg", b"nope"))
    assert Product.objects.count() == 0
    assert not (media_root / "products").exists()


def test_the_field_does_not_freeze_its_validator_into_migrations():
    _name, _path, _args, kwargs = Product._meta.get_field("photo").deconstruct()
    assert "validators" not in kwargs
    assert kwargs["max_side"] == 800
    assert kwargs["quality"] == 80
    assert kwargs["max_bytes"] == 50_000
    assert kwargs["thumb_side"] == 320
    assert kwargs["thumb_max_bytes"] == 12_000
