"""Tests for the Product model.

As in the other catalog tests, look-alike characters (Arabic/Persian yeh and
kaf) and the half space (ZWNJ) are written as escapes.
"""
import datetime

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

from apps.catalog.models import Product

from .conftest import make_image_bytes

pytestmark = pytest.mark.django_db

ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
ZWNJ = "\u200c"
SCORE_ARABIC_KAF = "\u0627\u0633" + ARABIC_KAF + "\u0648\u0631"  # اسکور, Arabic kaf
SCORE = "\u0627\u0633" + PERSIAN_KAF + "\u0648\u0631"


def make(product_fields, **overrides):
    return Product.objects.create(**{**product_fields, **overrides})


# --- required fields and defaults -------------------------------------------


def test_str_is_the_trade_name(product_fields):
    assert str(make(product_fields)) == product_fields["trade_name"]


def test_is_available_defaults_to_true(product_fields):
    assert make(product_fields).is_available is True


def test_photo_crops_and_pests_are_optional(product_fields):
    product = make(product_fields)
    assert not product.photo
    assert list(product.crops.all()) == []
    assert list(product.pests.all()) == []


@pytest.mark.parametrize(
    "missing", ["trade_name", "generic_name", "manufacturer", "importer", "country_of_origin"]
)
def test_required_text_fields_cannot_be_blank(product_fields, missing):
    product_fields[missing] = ""
    with pytest.raises(ValidationError) as exc:
        Product(**product_fields).full_clean()
    assert missing in exc.value.message_dict


def test_product_type_is_required(product_fields):
    del product_fields["product_type"]
    with pytest.raises(ValidationError) as exc:
        Product(**product_fields).full_clean()
    assert "product_type" in exc.value.message_dict


def test_usage_dosage_and_timing_are_optional(product_fields):
    product = make(product_fields)
    assert product.usage == ""
    assert product.dosage == ""
    assert product.timing == ""


def test_deleting_a_product_type_in_use_is_refused(product_fields, product_type):
    make(product_fields)
    with pytest.raises(IntegrityError), transaction.atomic():
        product_type.delete()


# --- text normalization -------------------------------------------------------


def test_text_fields_are_cleaned_on_save(product_fields):
    product_fields["trade_name"] = SCORE_ARABIC_KAF
    product_fields["dosage"] = "  \u06f2\u0644\u06cc\u062a\u0631 \u062f\u0631 \u0647\u06a9\u062a\u0627\u0631 "
    product = make(product_fields)
    product.refresh_from_db()
    assert product.trade_name == SCORE
    assert product.dosage == "\u06f2\u0644\u06cc\u062a\u0631 \u062f\u0631 \u0647\u06a9\u062a\u0627\u0631"


def test_usage_keeps_its_line_breaks(product_fields):
    multiline = (
        "\u0628\u0631\u0627\u06cc \u0645\u0628\u0627\u0631\u0632\u0647 \u0628\u0627 \u0633\u0641\u06cc\u062f\u06a9"
        "\n\u062f\u0631 \u0645\u0631\u062d\u0644\u0647 \u0631\u0634\u062f \u0631\u0648\u06cc\u0634\u06cc"
    )
    product_fields["usage"] = multiline
    product = make(product_fields)
    product.refresh_from_db()
    assert product.usage == multiline


def test_usage_still_unifies_letters(product_fields):
    product_fields["usage"] = ARABIC_KAF + "\u0632\u0627\u0631"
    product = make(product_fields)
    product.refresh_from_db()
    assert product.usage == PERSIAN_KAF + "\u0632\u0627\u0631"


# --- slugs -------------------------------------------------------------------


def test_slug_is_made_from_the_trade_name(product_fields):
    product_fields["trade_name"] = SCORE_ARABIC_KAF
    assert make(product_fields).slug == SCORE


def test_slug_does_not_change_when_the_name_is_fixed_later(product_fields):
    product = make(product_fields, trade_name=SCORE_ARABIC_KAF)
    original = product.slug
    product.trade_name = "\u0646\u0627\u0645 \u062f\u06cc\u06af\u0631"
    product.save()
    product.refresh_from_db()
    assert product.slug == original


def test_slug_collisions_are_numbered(product_fields):
    first = make(product_fields, trade_name=SCORE, generic_name="a")
    second = make(product_fields, trade_name=SCORE, generic_name="b")
    assert first.slug == SCORE
    assert second.slug == SCORE + "-2"


def test_an_explicit_slug_is_kept(product_fields):
    assert make(product_fields, slug="score").slug == "score"


# --- dates ---------------------------------------------------------------------


def test_no_dates_is_valid_and_has_dates_is_false(product_fields):
    product = make(product_fields)
    product.full_clean()
    assert product.has_dates is False


def test_both_dates_together_is_valid(product_fields):
    product_fields["production_date"] = datetime.date(2026, 1, 1)
    product_fields["expiry_date"] = datetime.date(2027, 1, 1)
    product = Product(**product_fields)
    product.full_clean()
    product.save()
    assert product.has_dates is True


def test_only_a_production_date_is_valid(product_fields):
    product_fields["production_date"] = datetime.date(2026, 1, 1)
    product = Product(**product_fields)
    product.full_clean()


def test_an_expiry_date_without_a_production_date_is_rejected_by_the_database(product_fields):
    product_fields["expiry_date"] = datetime.date(2027, 1, 1)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.create(**product_fields)


def test_expiry_on_or_before_production_is_rejected(product_fields):
    product_fields["production_date"] = datetime.date(2026, 6, 1)
    product_fields["expiry_date"] = datetime.date(2026, 6, 1)
    with pytest.raises(ValidationError) as exc:
        Product(**product_fields).full_clean()
    assert "expiry_date" in exc.value.message_dict

    product_fields["expiry_date"] = datetime.date(2026, 1, 1)
    with pytest.raises(ValidationError) as exc:
        Product(**product_fields).full_clean()
    assert "expiry_date" in exc.value.message_dict


# --- relations: crops and pests -----------------------------------------------


def test_crops_and_pests_can_be_attached(product_fields, crop, pest):
    product = make(product_fields)
    product.crops.add(crop)
    product.pests.add(pest)
    assert list(product.crops.all()) == [crop]
    assert list(product.pests.all()) == [pest]
    assert list(crop.products.all()) == [product]
    assert list(pest.products.all()) == [product]


# --- photo ---------------------------------------------------------------------


def test_a_photo_can_be_attached(product_fields):
    upload = SimpleUploadedFile("leaf.png", make_image_bytes(), content_type="image/png")
    product = make(product_fields, photo=upload)
    assert product.photo.name.startswith("products/")
    product.photo.delete(save=False)


def test_a_non_image_file_is_rejected(product_fields):
    upload = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")
    with pytest.raises(ValidationError) as exc:
        Product(photo=upload, **product_fields).full_clean()
    assert "photo" in exc.value.message_dict
