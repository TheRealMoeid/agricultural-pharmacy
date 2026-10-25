"""Tests for photo checking and conversion (D31). No database needed."""
import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.core import images
from apps.core.images import (
    MAX_UPLOAD_BYTES,
    MIN_SIDE,
    ImageRejected,
    encode_webp,
    load_image,
    process_image,
    thumb_name,
    validate_image_upload,
)


def make_upload(fmt="JPEG", size=(100, 100), mode="RGB", color="green", name="photo.jpg", **save_kwargs):
    buffer = io.BytesIO()
    Image.new(mode, size, color).save(buffer, format=fmt, **save_kwargs)
    return SimpleUploadedFile(name, buffer.getvalue())


def result_image(content) -> Image.Image:
    image = Image.open(io.BytesIO(content.read()))
    image.load()
    return image


# --- output format and size -----------------------------------------------------


def test_the_result_is_a_webp_with_a_webp_name():
    content = process_image(make_upload())
    assert content.name.endswith(".webp")
    assert content.read(12)[8:12] == b"WEBP"
    content.seek(0)
    assert result_image(content).format == "WEBP"


def test_the_name_is_random_and_ignores_the_original_name():
    first = process_image(make_upload(name="\u0627\u0633\u06a9\u0648\u0631 IMG_2231.jpg"))
    second = process_image(make_upload(name="\u0627\u0633\u06a9\u0648\u0631 IMG_2231.jpg"))
    assert "IMG" not in first.name
    assert first.name != second.name


def test_a_large_landscape_photo_is_shrunk_keeping_its_shape():
    image = result_image(process_image(make_upload(size=(2000, 1000))))
    assert image.size == (800, 400)


def test_a_large_portrait_photo_is_shrunk_by_its_longest_side():
    image = result_image(process_image(make_upload(size=(1000, 3000))))
    assert image.height == 800
    assert image.width in (266, 267)


def test_a_small_photo_is_never_enlarged():
    image = result_image(process_image(make_upload(size=(200, 100))))
    assert image.size == (200, 100)


def test_max_side_can_be_chosen_per_field():
    image = result_image(process_image(make_upload(size=(2000, 1000)), max_side=100))
    assert image.size == (100, 50)


def test_quality_changes_the_file_size():
    noise = Image.effect_noise((300, 300), 60).convert("RGB")
    buffer = io.BytesIO()
    noise.save(buffer, format="PNG")
    upload = SimpleUploadedFile("noise.png", buffer.getvalue())
    # A huge budget, so that only `quality` decides.
    low = len(process_image(upload, quality=10, max_bytes=10**9).read())
    high = len(process_image(upload, quality=95, max_bytes=10**9).read())
    assert low < high


def test_a_processed_file_can_be_processed_again():
    once = process_image(make_upload())
    twice = process_image(once)
    assert result_image(twice).format == "WEBP"


# --- orientation, metadata, colour modes ------------------------------------------


def test_exif_rotation_is_applied_to_the_pixels():
    exif = Image.Exif()
    exif[0x0112] = 6  # "rotate 90 degrees clockwise to display"
    upload = make_upload(size=(200, 100), exif=exif)
    image = result_image(process_image(upload))
    assert image.size == (100, 200)


def test_camera_metadata_is_not_kept():
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"
    upload = make_upload(exif=exif)
    assert b"SecretCameraMaker" in upload.read()  # it really is in the upload
    upload.seek(0)
    content = process_image(upload)
    assert b"SecretCameraMaker" not in content.read()


def test_transparency_is_kept():
    buffer = io.BytesIO()
    Image.new("RGBA", (50, 50), (255, 0, 0, 0)).save(buffer, format="PNG")
    image = result_image(process_image(SimpleUploadedFile("t.png", buffer.getvalue())))
    assert image.mode == "RGBA"
    assert image.getpixel((10, 10))[3] == 0


def test_a_palette_png_with_transparency_keeps_it():
    palette = Image.new("P", (50, 50), 0)
    buffer = io.BytesIO()
    palette.save(buffer, format="PNG", transparency=0)
    image = result_image(process_image(SimpleUploadedFile("p.png", buffer.getvalue())))
    assert image.mode == "RGBA"
    assert image.getpixel((10, 10))[3] == 0


def test_a_photo_without_transparency_is_stored_without_an_alpha_channel():
    image = result_image(process_image(make_upload()))
    assert image.mode == "RGB"


def test_a_cmyk_jpeg_becomes_rgb():
    image = result_image(process_image(make_upload(mode="CMYK", color=(0, 0, 0, 0))))
    assert image.mode == "RGB"


@pytest.mark.parametrize("fmt, name", [("JPEG", "a.jpg"), ("PNG", "a.png"), ("WEBP", "a.webp")])
def test_jpeg_png_and_webp_are_accepted(fmt, name):
    assert result_image(process_image(make_upload(fmt=fmt, name=name))).format == "WEBP"


def test_a_file_is_judged_by_its_content_not_its_name():
    upload = make_upload(fmt="PNG", name="actually-a-png.jpg")
    assert result_image(process_image(upload)).format == "WEBP"


# --- refusals -------------------------------------------------------------------------


@pytest.mark.parametrize("fmt, name", [("GIF", "a.gif"), ("BMP", "a.bmp"), ("TIFF", "a.tiff")])
def test_other_image_formats_are_refused(fmt, name):
    with pytest.raises(ImageRejected) as exc:
        process_image(make_upload(fmt=fmt, name=name, mode="RGB"))
    assert "jpg" in str(exc.value)


def test_text_pretending_to_be_a_photo_is_refused():
    with pytest.raises(ImageRejected):
        process_image(SimpleUploadedFile("photo.jpg", b"this is not an image"))


def test_an_empty_file_is_refused_with_its_own_message():
    with pytest.raises(ImageRejected) as exc:
        process_image(SimpleUploadedFile("photo.jpg", b""))
    assert "خالی" in str(exc.value)


def test_a_truncated_jpeg_is_refused():
    full = make_upload(size=(400, 400)).read()
    with pytest.raises(ImageRejected):
        process_image(SimpleUploadedFile("cut.jpg", full[: len(full) // 2]))


def test_a_file_over_the_size_limit_is_refused_before_decoding():
    too_big = SimpleUploadedFile("big.jpg", b"0" * (MAX_UPLOAD_BYTES + 1))
    with pytest.raises(ImageRejected) as exc:
        process_image(too_big)
    assert "مگابایت" in str(exc.value)


def test_a_file_exactly_at_the_size_limit_is_not_refused_for_its_size():
    at_limit = SimpleUploadedFile("edge.jpg", b"0" * MAX_UPLOAD_BYTES)
    with pytest.raises(ImageRejected) as exc:
        process_image(at_limit)
    assert "مگابایت" not in str(exc.value)  # refused as "not an image", not as "too big"


def test_too_many_pixels_is_refused(monkeypatch):
    monkeypatch.setattr(images, "MAX_PIXELS", 100)
    with pytest.raises(ImageRejected):
        process_image(make_upload(size=(11, 10)))


def test_exactly_the_pixel_limit_is_accepted(monkeypatch):
    monkeypatch.setattr(images, "MAX_PIXELS", 100)
    assert result_image(process_image(make_upload(size=(10, 10)))).size == (10, 10)


# --- the validator ------------------------------------------------------------------------


def test_the_validator_accepts_a_good_upload_and_rewinds_the_file():
    upload = make_upload()
    validate_image_upload(upload)
    assert upload.tell() == 0


def test_the_validator_turns_a_refusal_into_a_validation_error():
    with pytest.raises(ValidationError) as exc:
        validate_image_upload(SimpleUploadedFile("x.jpg", b"nope"))
    assert exc.value.code == "image_rejected"  # not Django's own "invalid_image", which would replace the message
    assert "تصویر معتبری نیست" in exc.value.message


def test_the_validator_does_not_reopen_a_file_that_is_already_stored():
    class Stored:
        _committed = True

    validate_image_upload(Stored())  # would blow up if it tried to read it


# --- the byte budget ------------------------------------------------------------------------


def noisy(size=(500, 500)):
    return Image.effect_noise(size, 60).convert("RGB")


def test_a_picture_that_fits_the_budget_is_left_alone():
    flat = Image.new("RGB", (600, 400), "green")
    out = Image.open(io.BytesIO(encode_webp(flat, max_bytes=50_000)))
    assert out.size == (600, 400)


def test_quality_is_lowered_before_the_picture_is_made_smaller():
    image = noisy()
    at_80 = len(encode_webp(image, quality=80, max_bytes=10**9))
    at_floor = len(encode_webp(image, quality=images.MIN_QUALITY, max_bytes=10**9))
    budget = (at_80 + at_floor) // 2  # reachable by quality alone
    data = encode_webp(image, quality=80, max_bytes=budget)
    assert len(data) <= budget
    assert Image.open(io.BytesIO(data)).size == (500, 500)  # not made smaller


def test_quality_goes_down_one_step_at_a_time_not_straight_to_the_floor():
    image = noisy()
    at_80 = len(encode_webp(image, quality=80, max_bytes=10**9))
    at_floor = len(encode_webp(image, quality=images.MIN_QUALITY, max_bytes=10**9))
    data = encode_webp(image, quality=80, max_bytes=at_80 - 1)  # just over budget at 80
    assert at_floor < len(data) <= at_80 - 1


def test_a_picture_exactly_on_budget_is_accepted_as_it_is():
    image = noisy()
    first = encode_webp(image, quality=80, max_bytes=10**9)
    assert encode_webp(image, quality=80, max_bytes=len(first)) == first


def test_each_shrink_makes_the_picture_15_percent_smaller():
    image = noisy()
    at_floor = len(encode_webp(image, quality=images.MIN_QUALITY, max_bytes=10**9))
    data = encode_webp(image, quality=80, max_bytes=at_floor - 1)  # floor quality is just not enough
    assert Image.open(io.BytesIO(data)).size == (425, 425)


def test_the_picture_is_made_smaller_when_floor_quality_is_not_enough():
    image = noisy()
    at_floor = len(encode_webp(image, quality=images.MIN_QUALITY, max_bytes=10**9))
    data = encode_webp(image, quality=80, max_bytes=at_floor // 2)
    out = Image.open(io.BytesIO(data))
    assert out.width < 500
    assert len(data) < at_floor


def test_an_impossible_budget_gives_the_smallest_attempt_not_an_error():
    data = encode_webp(noisy(), max_bytes=1)
    out = Image.open(io.BytesIO(data))
    assert len(data) > 1  # the budget was not met, and that is accepted
    assert min(out.size) >= MIN_SIDE  # but it did not shrink without limit


def test_the_budget_applies_to_process_image_too():
    upload = SimpleUploadedFile("n.png", _png_bytes(noisy()))
    roomy = len(process_image(upload, max_bytes=10**9).read())
    tight = len(process_image(upload, max_bytes=roomy // 2).read())
    assert tight < roomy


def _png_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_load_image_returns_an_upright_rgb_picture():
    exif = Image.Exif()
    exif[0x0112] = 6
    image = load_image(make_upload(size=(200, 100), exif=exif))
    assert image.size == (100, 200)
    assert image.mode == "RGB"


# --- thumbnail names -------------------------------------------------------------------------


def test_thumb_name_goes_next_to_the_main_file():
    assert thumb_name("products/ab12.webp") == "products/ab12_thumb.webp"
    assert thumb_name("ab12.webp") == "ab12_thumb.webp"


# --- the numbers written down in D31 ---------------------------------------------------------


def test_the_numbers_are_the_ones_recorded_in_decision_d31():
    assert (images.DEFAULT_MAX_SIDE, images.DEFAULT_MAX_BYTES) == (800, 50_000)
    assert (images.DEFAULT_THUMB_SIDE, images.DEFAULT_THUMB_MAX_BYTES) == (320, 12_000)
    assert images.DEFAULT_QUALITY == 80
    assert (images.MIN_QUALITY, images.QUALITY_STEP) == (40, 10)
    assert (images.SHRINK_FACTOR, images.MIN_SIDE) == (0.85, 200)
    assert (images.MAX_UPLOAD_BYTES, images.MAX_PIXELS) == (10 * 1024 * 1024, 40_000_000)
