"""Tests for the public product search (D38).

Look-alike characters (Arabic and Persian yeh and kaf), ZWNJ and the madda on
alef are written as escapes, as in the other catalog tests.
"""
import pytest

from apps.catalog.models import Crop, Pest, Product, ProductType
from apps.catalog.search import RANK_NAME, RANK_TAG, RANK_USAGE, search

pytestmark = pytest.mark.django_db

ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
ZWNJ = "\u200c"
WITH_ZWNJ = "\u0633\u0627\u0642\u0647" + ZWNJ + "\u062e\u0648\u0627\u0631"  # ساقه‌خوار
WITHOUT_ZWNJ = "\u0633\u0627\u0642\u0647\u062e\u0648\u0627\u0631"
PLUM = "\u0622\u0644\u0648"  # آلو
PLUM_NO_MADDA = "\u0627\u0644\u0648"  # الو
WHEAT = "\u06af\u0646\u062f\u0645"  # گندم
SCORE = "\u0627\u0633" + PERSIAN_KAF + "\u0648\u0631"  # اسکور
SCORE_ARABIC_KAF = "\u0627\u0633" + ARABIC_KAF + "\u0648\u0631"


def make(fields, **overrides):
    return Product.objects.create(**{**fields, **overrides})


def names(results):
    return [p.trade_name for p in results]


# --- empty query ---------------------------------------------------------------------------


def test_an_empty_query_returns_everything_in_the_products_own_order(product_fields):
    b = make(product_fields, trade_name="b")
    a = make(product_fields, trade_name="a")
    assert search("") == [a, b]


def test_a_whitespace_only_query_also_returns_everything(product_fields):
    make(product_fields)
    assert len(search("   \u200c  ")) == 1


def test_unavailable_products_are_returned_too(product_fields):
    # D7: an unavailable product stays visible, search does not hide it.
    product = make(product_fields, is_available=False)
    assert search(product.trade_name) == [product]


# --- which fields a word can match -----------------------------------------------------------


def test_a_word_matches_the_trade_name(product_fields):
    product = make(product_fields, trade_name=SCORE)
    make(product_fields, trade_name="\u062f\u06cc\u06af\u0631")  # دیگر
    assert search(SCORE) == [product]


def test_a_word_matches_the_generic_name(product_fields):
    product = make(product_fields, generic_name="Mancozeb 80% WP")
    make(product_fields, generic_name="other")
    assert search("mancozeb") == [product]


def test_a_word_matches_the_usage_text(product_fields):
    product = make(product_fields, usage="\u0628\u0631\u0627\u06cc " + WHEAT)
    make(product_fields, usage="\u0628\u0631\u0627\u06cc \u0686\u0627\u06cc")
    assert search(WHEAT) == [product]


def test_a_word_matches_a_crops_name(product_fields, crop):
    product = make(product_fields)
    product.crops.add(crop)
    make(product_fields)  # no crop at all
    assert search(crop.name) == [product]


def test_a_word_matches_a_pests_name(product_fields, pest):
    product = make(product_fields)
    product.pests.add(pest)
    make(product_fields)
    assert search(pest.name) == [product]


def test_a_word_matches_a_crops_alternate_name(product_fields):
    crop = Crop.objects.create(name=PLUM, alternate_names="plum")
    product = make(product_fields)
    product.crops.add(crop)
    assert search("plum") == [product]


def test_a_query_word_can_be_a_strict_substring_of_a_crops_name(product_fields):
    # "ساقه" is a proper prefix of "ساقه‌خوار" once the half space is removed:
    # a true substring match, not the whole key, so a lookup by equality would miss it.
    crop = Crop.objects.create(name="\u06a9\u0631\u0645 " + WITH_ZWNJ)  # کرم ساقه‌خوار
    product = make(product_fields)
    product.crops.add(crop)
    assert search("\u0633\u0627\u0642\u0647") == [product]  # "ساقه"


def test_product_type_name_is_not_searched(product_fields, product_type):
    make(product_fields)
    assert search(product_type.name) == []


# --- typing style ----------------------------------------------------------------------------


def test_search_ignores_which_kaf_was_typed(product_fields):
    product = make(product_fields, trade_name=SCORE)
    assert search(SCORE_ARABIC_KAF) == [product]


def test_search_ignores_the_half_space(product_fields):
    product = make(product_fields, usage=WITH_ZWNJ)
    assert search(WITHOUT_ZWNJ) == [product]


def test_search_finds_alef_with_madda_when_typed_without_it(product_fields):
    product = make(product_fields, usage=PLUM)
    assert search(PLUM_NO_MADDA) == [product]


def test_persian_digits_in_the_query_match_ascii_digits_in_the_product(product_fields):
    product = make(product_fields, generic_name="Score 250 EC")
    assert search("\u06f2\u06f5\u06f0") == [product]


def test_latin_matches_are_case_insensitive(product_fields):
    product = make(product_fields, trade_name="Topsin")
    assert search("TOPSIN") == [product]


# --- every word must match somewhere -------------------------------------------------------


def test_two_words_can_match_different_fields_of_the_same_product(product_fields):
    product = make(product_fields, trade_name=SCORE, usage="\u0628\u0631\u0627\u06cc " + WHEAT)
    assert search(SCORE + " " + WHEAT) == [product]


def test_a_word_that_matches_nowhere_excludes_the_product(product_fields):
    make(product_fields, trade_name=SCORE)
    assert search(SCORE + " \u0646\u0627\u06cc\u0627\u0628") == []  # "ناياب" matches nothing


def test_a_second_word_must_also_match_even_if_the_first_matched_everything(product_fields):
    a = make(product_fields, trade_name=SCORE, usage=WHEAT)
    make(product_fields, trade_name=SCORE)  # matches the first word only
    assert search(SCORE + " " + WHEAT) == [a]


# --- ranking ------------------------------------------------------------------------------------


def test_the_ranks_are_ordered_name_before_usage_before_tag():
    assert RANK_NAME < RANK_USAGE < RANK_TAG


def test_a_name_match_ranks_above_a_usage_only_match(product_fields):
    by_name = make(product_fields, trade_name="b " + SCORE)
    by_usage = make(product_fields, trade_name="a", usage=SCORE)
    assert search(SCORE) == [by_name, by_usage]


def test_a_usage_match_ranks_above_a_tag_only_match(product_fields, crop):
    by_usage = make(product_fields, trade_name="b", usage=crop.name)
    by_tag = make(product_fields, trade_name="a")
    by_tag.crops.add(crop)
    assert search(crop.name) == [by_usage, by_tag]


def test_a_name_match_ranks_above_a_tag_only_match(product_fields, crop):
    by_name = make(product_fields, trade_name="b " + crop.name)
    by_tag = make(product_fields, trade_name="a")
    by_tag.crops.add(crop)
    assert search(crop.name) == [by_name, by_tag]


def test_one_word_matching_the_name_is_enough_to_rank_as_a_name_match(product_fields, crop):
    # word 1 only in the name, word 2 only on a crop: still RANK_NAME overall.
    product = make(product_fields, trade_name=SCORE)
    product.crops.add(crop)
    other = make(product_fields, trade_name="b", usage=SCORE + " " + crop.name)
    assert search(SCORE + " " + crop.name) == [product, other]


def test_a_product_matching_in_both_the_name_and_the_usage_still_ranks_as_a_name_match(product_fields):
    pure_usage = make(product_fields, trade_name="a", usage=SCORE)
    both = make(product_fields, trade_name="z " + SCORE, usage=SCORE)
    assert search(SCORE) == [both, pure_usage]


def test_within_a_rank_products_keep_their_default_alphabetical_order(product_fields):
    b = make(product_fields, trade_name="b " + SCORE)
    a = make(product_fields, trade_name="a " + SCORE)
    assert search(SCORE) == [a, b]


# --- the products argument -----------------------------------------------------------------------


def test_a_starting_queryset_narrows_the_search(product_fields, product_type):
    in_type = make(product_fields, trade_name=SCORE)
    other_type = ProductType.objects.create(name="\u062d\u0634\u0631\u0647\u200c\u06a9\u0634")
    make({**product_fields, "product_type": other_type}, trade_name=SCORE)
    assert search(SCORE, Product.objects.filter(product_type=product_type)) == [in_type]


def test_an_empty_query_also_respects_the_starting_queryset(product_fields):
    make(product_fields, trade_name="a")
    other_type = ProductType.objects.create(name="\u062d\u0634\u0631\u0647\u200c\u06a9\u0634")
    make({**product_fields, "product_type": other_type}, trade_name="b")
    assert names(search("", Product.objects.filter(product_type=other_type))) == ["b"]


def test_no_argument_searches_the_whole_catalog(product_fields):
    make(product_fields, trade_name=SCORE)
    assert len(search(SCORE)) == 1


# --- edge cases and robustness ---------------------------------------------------------------------


def test_a_product_with_no_crops_or_pests_does_not_error(product_fields):
    make(product_fields, trade_name=SCORE)
    assert search(SCORE, Product.objects.all())  # does not raise


def test_a_search_result_is_a_plain_list(product_fields):
    make(product_fields)
    assert isinstance(search(""), list)
    assert isinstance(search("x"), list)


def test_searching_for_a_word_nobody_has_returns_nothing(product_fields):
    make(product_fields)
    assert search("\u0646\u0627\u06cc\u0627\u0628\u06cc\u0627\u0628") == []  # a made-up word


def test_crops_and_pests_are_prefetched_in_one_query_each(product_fields, crop, pest, django_assert_max_num_queries):
    for i in range(3):
        product = make(product_fields, trade_name=f"{SCORE} {i}")
        product.crops.add(crop)
        product.pests.add(pest)
    with django_assert_max_num_queries(3):  # products, crops prefetch, pests prefetch
        search(crop.name)
