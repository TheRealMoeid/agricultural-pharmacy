"""Tests for ProductType, Crop and Pest.

As in test_text.py, characters that look the same on screen (Arabic and Persian
yeh and kaf, ZWNJ, the madda on alef) are written as escapes. Do not "fix" them
into literal letters.
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.catalog.models import Crop, Pest, ProductType

pytestmark = pytest.mark.django_db

ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
ARABIC_YEH = "\u064a"
PERSIAN_YEH = "\u06cc"
ZWNJ = "\u200c"
ALEF = "\u0627"
ALEF_MADDA = "\u0622"

ALL_MODELS = [ProductType, Crop, Pest]
TAG_MODELS = [Crop, Pest]

# "ساقه‌خوار" with and without the half space.
WITH_ZWNJ = "\u0633\u0627\u0642\u0647" + ZWNJ + "\u062e\u0648\u0627\u0631"
WITHOUT_ZWNJ = "\u0633\u0627\u0642\u0647\u062e\u0648\u0627\u0631"
# "کلزا" (rapeseed), typed with each kaf.
KOLZA = PERSIAN_KAF + "\u0644\u0632\u0627"
KOLZA_ARABIC = ARABIC_KAF + "\u0644\u0632\u0627"
WHEAT = "\u06af\u0646\u062f\u0645"  # گندم


@pytest.fixture(params=ALL_MODELS, ids=lambda m: m.__name__)
def model(request):
    return request.param


@pytest.fixture(params=TAG_MODELS, ids=lambda m: m.__name__)
def tag_model(request):
    return request.param


# --- names -----------------------------------------------------------------


def test_str_is_the_name(model):
    assert str(model.objects.create(name=WHEAT)) == WHEAT


def test_name_is_cleaned_when_saved(model):
    item = model.objects.create(name="  " + KOLZA_ARABIC + "   \u0645\u062f\u0631\u0646 ")
    item.refresh_from_db()
    assert item.name == KOLZA + " \u0645\u062f\u0631\u0646"


def test_stored_name_keeps_its_spelling_but_the_key_folds_alef(model):
    item = model.objects.create(name=ALEF_MADDA + "\u0644\u0648")  # آلو (plum)
    item.refresh_from_db()
    assert item.name == ALEF_MADDA + "\u0644\u0648"
    assert item.name_key == ALEF + "\u0644\u0648"


def test_the_key_drops_zwnj_but_the_name_keeps_it(model):
    item = model.objects.create(name=WITH_ZWNJ)
    item.refresh_from_db()
    assert item.name == WITH_ZWNJ
    assert item.name_key == WITHOUT_ZWNJ


def test_a_name_that_grows_when_cleaned_is_rejected_instead_of_crashing(model):
    # U+FDFA is one character that NFKC turns into eighteen. Six of them pass the
    # 100-character field check as typed, then no longer fit once cleaned.
    item = model(name="\ufdfa" * 6)
    with pytest.raises(ValidationError) as exc:
        item.full_clean()
    assert "name" in exc.value.message_dict


def test_a_blank_name_is_rejected(model):
    with pytest.raises(ValidationError) as exc:
        model(name="  \u200c ").full_clean()
    assert "name" in exc.value.message_dict


# --- uniqueness --------------------------------------------------------------


def test_the_same_name_typed_with_another_kaf_is_a_duplicate(model):
    model.objects.create(name=KOLZA)
    with pytest.raises(ValidationError) as exc:
        model(name=KOLZA_ARABIC).full_clean()
    assert list(exc.value.message_dict) == ["name"]


def test_a_half_space_makes_no_difference_to_uniqueness(model):
    model.objects.create(name=WITH_ZWNJ)
    with pytest.raises(ValidationError) as exc:
        model(name=WITHOUT_ZWNJ).full_clean()
    assert "name" in exc.value.message_dict


def test_the_duplicate_message_shows_the_existing_spelling(model):
    model.objects.create(name=WITH_ZWNJ)
    with pytest.raises(ValidationError) as exc:
        model(name=WITHOUT_ZWNJ).full_clean()
    assert WITH_ZWNJ in exc.value.message_dict["name"][0]


def test_an_existing_row_does_not_clash_with_itself(model):
    item = model.objects.create(name=KOLZA)
    item.full_clean()
    item.name = KOLZA_ARABIC  # same name, retyped
    item.full_clean()


def test_different_names_are_fine(model):
    model.objects.create(name=KOLZA)
    model(name=WHEAT).full_clean()


def test_the_database_refuses_a_duplicate_even_without_validation(model):
    model.objects.create(name=KOLZA)
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(name=KOLZA_ARABIC)


def test_the_same_name_may_exist_in_different_tables():
    # A word can be both a crop and a pest-related term. Tables do not compete.
    Crop.objects.create(name=WHEAT)
    Pest.objects.create(name=WHEAT)
    ProductType.objects.create(name=WHEAT)


# --- slugs -------------------------------------------------------------------


def test_slug_comes_from_the_name_without_the_half_space(model):
    assert model.objects.create(name=WITH_ZWNJ).slug == WITHOUT_ZWNJ


def test_slug_turns_spaces_into_hyphens(model):
    name = "\u06a9\u0631\u0645 " + WITH_ZWNJ  # کرم ساقه‌خوار
    assert model.objects.create(name=name).slug == "\u06a9\u0631\u0645-" + WITHOUT_ZWNJ


def test_slug_does_not_change_when_the_name_is_fixed_later(model):
    item = model.objects.create(name=KOLZA_ARABIC)
    original = item.slug
    item.name = "\u06a9\u0644\u0632\u0627\u06cc \u0628\u0647\u0627\u0631\u0647"
    item.save()
    item.refresh_from_db()
    assert item.slug == original


def test_slugs_that_would_collide_get_a_number(model):
    # Different names (the "!" makes the keys differ) that make the same slug.
    first = model.objects.create(name=WHEAT)
    second = model.objects.create(name=WHEAT + "!")
    third = model.objects.create(name=WHEAT + "?")
    assert [first.slug, second.slug, third.slug] == [WHEAT, WHEAT + "-2", WHEAT + "-3"]


def test_a_name_with_no_letters_still_gets_a_slug(model):
    assert model.objects.create(name="!!!").slug == "item"
    assert model.objects.create(name="???").slug == "item-2"


def test_a_slug_given_explicitly_is_kept(model):
    assert model.objects.create(name=WHEAT, slug="wheat").slug == "wheat"


def test_resaving_does_not_renumber_the_slug(model):
    model.objects.create(name=WHEAT)
    second = model.objects.create(name=WHEAT + "!")
    second.save()
    second.refresh_from_db()
    assert second.slug == WHEAT + "-2"


# --- alternate names (Crop and Pest) -----------------------------------------


def test_alternate_names_are_tidied_and_deduplicated(tag_model):
    item = tag_model.objects.create(
        name=WHEAT,
        alternate_names=(
            WHEAT + " \u062f\u06cc\u0645\r\n"  # "گندم دیم"
            "\r\n"
            "  " + WHEAT + "   \u062f\u06cc\u0645 \n"  # same again, extra spaces
            "wheat\n"
            "  Wheat\n"  # same key as the line above
            + WHEAT  # same as the name itself
        ),
    )
    item.refresh_from_db()
    assert item.alternate_names == WHEAT + " \u062f\u06cc\u0645\nwheat"
    assert item.alternate_name_list == [WHEAT + " \u062f\u06cc\u0645", "wheat"]


def test_alternate_name_spelled_differently_but_same_key_as_the_name_is_dropped(tag_model):
    item = tag_model.objects.create(name=WITH_ZWNJ, alternate_names=WITHOUT_ZWNJ)
    assert item.alternate_names == ""
    assert item.alternate_name_list == []


def test_no_alternate_names_is_fine(tag_model):
    assert tag_model.objects.create(name=WHEAT).alternate_name_list == []


def test_search_keys_cover_the_name_and_every_alternate(tag_model):
    item = tag_model.objects.create(
        name=ALEF_MADDA + "\u0644\u0648",  # آلو
        alternate_names="Plum\n" + ALEF_MADDA + "\u0644\u0648\u06cc",  # آلوی
    )
    assert item.search_keys() == {
        ALEF + "\u0644\u0648",
        "plum",
        ALEF + "\u0644\u0648\u06cc",
    }


def test_alternate_name_clash_does_not_block_a_new_row(tag_model):
    # Alternates are for search only; they are not required to be unique.
    tag_model.objects.create(name=WHEAT, alternate_names="grain")
    tag_model.objects.create(name=KOLZA, alternate_names="grain")


def test_product_type_has_no_alternate_names():
    assert not hasattr(ProductType, "alternate_names")


# --- ordering ----------------------------------------------------------------


def test_product_types_are_ordered_by_order_then_name():
    last = ProductType.objects.create(name="\u0632", order=1)
    middle = ProductType.objects.create(name="\u0627", order=1)
    first = ProductType.objects.create(name="\u0645", order=0)
    assert list(ProductType.objects.all()) == [first, middle, last]


def test_crops_and_pests_are_ordered_by_name(tag_model):
    later = tag_model.objects.create(name="\u0632")
    earlier = tag_model.objects.create(name="\u0627")
    assert list(tag_model.objects.all()) == [earlier, later]
