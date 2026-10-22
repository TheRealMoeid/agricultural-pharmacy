"""Tests for the Persian text helpers.

Arabic and Persian yeh/kaf look identical on screen, so the characters that
matter are written as escapes. Do not "fix" them into literal letters.
"""
import pytest

from apps.core.text import (
    normalize_digits,
    normalize_for_search,
    normalize_letters,
    normalize_text,
)

ARABIC_YEH = "\u064a"  # ي
ALEF_MAKSURA = "\u0649"  # ى
ARABIC_KAF = "\u0643"  # ك
PERSIAN_YEH = "\u06cc"  # ی
PERSIAN_KAF = "\u06a9"  # ک
ZWNJ = "\u200c"
NBSP = "\u00a0"
TATWEEL = "\u0640"


class TestNormalizeDigits:
    @pytest.mark.parametrize(
        "typed, expected",
        [
            ("\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9", "0123456789"),
            ("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669", "0123456789"),
            ("0123456789", "0123456789"),
            ("\u06f0\u06f9\u06f1\u06f1\u06f2\u06f7\u06f4\u06f7\u06f6\u06f2\u06f8", "09112747628"),
            ("\u06f2\u06f5\u06f0 cc", "250 cc"),  # mixed with other characters
        ],
    )
    def test_converts_to_ascii(self, typed, expected):
        assert normalize_digits(typed) == expected

    def test_none_and_empty(self):
        assert normalize_digits(None) == ""
        assert normalize_digits("") == ""


class TestNormalizeLetters:
    def test_arabic_yeh_becomes_persian_yeh(self):
        assert normalize_letters("\u0639\u0644" + ARABIC_YEH) == "\u0639\u0644" + PERSIAN_YEH

    def test_alef_maksura_becomes_persian_yeh(self):
        assert normalize_letters("\u0645\u0648\u0633" + ALEF_MAKSURA) == "\u0645\u0648\u0633" + PERSIAN_YEH

    def test_arabic_kaf_becomes_persian_kaf(self):
        assert normalize_letters(ARABIC_KAF + "\u0634\u0627\u0648\u0631\u0632") == PERSIAN_KAF + "\u0634\u0627\u0648\u0631\u0632"

    def test_already_persian_is_unchanged(self):
        word = PERSIAN_KAF + "\u0634\u0627\u0648\u0631\u0632 " + "\u0639\u0644" + PERSIAN_YEH
        assert normalize_letters(word) == word

    def test_removes_tatweel(self):
        assert normalize_letters(PERSIAN_KAF + TATWEEL + TATWEEL + "\u0634") == PERSIAN_KAF + "\u0634"

    def test_removes_vowel_marks(self):
        # kasra, fatha, damma, shadda on a few letters
        marked = "\u0645\u064f\u0628\u064e\u0627\u0631\u0651\u064d\u0643"
        assert normalize_letters(marked) == "\u0645\u0628\u0627\u0631" + PERSIAN_KAF

    def test_alef_with_madda_is_not_folded_into_plain_alef(self):
        # "آب" (water) and "اب" are different words.
        assert normalize_letters("\u0622\u0628") == "\u0622\u0628"
        assert normalize_letters("\u0622\u0628") != normalize_letters("\u0627\u0628")

    def test_hamza_forms_are_left_alone(self):
        assert normalize_letters("\u0623\u062d\u0645\u062f") == "\u0623\u062d\u0645\u062f"

    def test_fullwidth_digits_are_folded_by_nfkc(self):
        assert normalize_letters("\uff11\uff12\uff13") == "123"

    def test_keeps_newlines_and_spacing(self):
        assert normalize_letters("a  b\n\nc") == "a  b\n\nc"

    def test_none_and_empty(self):
        assert normalize_letters(None) == ""
        assert normalize_letters("") == ""


class TestNormalizeText:
    def test_collapses_and_trims_whitespace(self):
        assert normalize_text("  \u0642\u0627\u0631\u0686   \u06a9\u0634 \t\n ") == "\u0642\u0627\u0631\u0686 \u06a9\u0634"

    def test_non_breaking_space_counts_as_whitespace(self):
        assert normalize_text("a" + NBSP + NBSP + "b") == "a b"

    def test_keeps_zwnj_between_letters(self):
        word = "\u0642\u0627\u0631\u0686" + ZWNJ + "\u06a9\u0634"
        assert normalize_text(word) == word

    def test_zwnj_next_to_space_is_dropped(self):
        assert normalize_text("a" + ZWNJ + " b") == "a b"
        assert normalize_text("a " + ZWNJ + "b") == "a b"

    def test_repeated_zwnj_collapses_to_one(self):
        assert normalize_text("a" + ZWNJ * 3 + "b") == "a" + ZWNJ + "b"

    def test_zwnj_at_the_edges_is_trimmed(self):
        assert normalize_text(ZWNJ + "a" + ZWNJ) == "a"

    def test_removes_invisible_direction_marks(self):
        pasted = "\u200f\u202bab\u202c\u200e \u200bcd\ufeff"
        assert normalize_text(pasted) == "ab cd"

    def test_digits_are_kept_as_typed(self):
        assert normalize_text("\u06f2\u06f5\u06f0") == "\u06f2\u06f5\u06f0"

    def test_unifies_letters_too(self):
        assert normalize_text(ARABIC_KAF + ARABIC_YEH) == PERSIAN_KAF + PERSIAN_YEH

    def test_none_empty_and_whitespace_only(self):
        assert normalize_text(None) == ""
        assert normalize_text("") == ""
        assert normalize_text(" \t\n" + ZWNJ) == ""


class TestNormalizeForSearch:
    def test_zwnj_spelling_variants_give_the_same_key(self):
        # قارچ‌کش, قارچکش and a version typed on an Arabic keyboard.
        with_zwnj = "\u0642\u0627\u0631\u0686" + ZWNJ + "\u06a9\u0634"
        without = "\u0642\u0627\u0631\u0686\u06a9\u0634"
        arabic_kaf = "\u0642\u0627\u0631\u0686" + ZWNJ + ARABIC_KAF + "\u0634"
        assert normalize_for_search(with_zwnj) == normalize_for_search(without)
        assert normalize_for_search(arabic_kaf) == normalize_for_search(without)

    def test_a_real_space_is_kept(self):
        spaced = "\u0642\u0627\u0631\u0686 \u06a9\u0634"
        joined = "\u0642\u0627\u0631\u0686\u06a9\u0634"
        assert normalize_for_search(spaced) != normalize_for_search(joined)
        assert normalize_for_search(spaced) == spaced

    def test_digits_become_ascii(self):
        assert normalize_for_search("\u06f2\u06f5\u06f0") == "250"
        assert normalize_for_search("\u0662\u0665\u0660") == "250"

    def test_latin_is_case_folded(self):
        assert normalize_for_search("Mancozeb") == "mancozeb"
        assert normalize_for_search("MANCOZEB 80% WP") == "mancozeb 80% wp"

    def test_mixed_persian_and_latin_with_persian_digits(self):
        assert normalize_for_search("Score \u06f2\u06f5\u06f0 EC") == "score 250 ec"

    def test_arabic_and_persian_typing_match(self):
        arabic = ARABIC_KAF + "\u0634\u0627\u0648\u0631\u0632" + ARABIC_YEH
        persian = PERSIAN_KAF + "\u0634\u0627\u0648\u0631\u0632" + PERSIAN_YEH
        assert normalize_for_search(arabic) == normalize_for_search(persian)

    def test_none_and_empty(self):
        assert normalize_for_search(None) == ""
        assert normalize_for_search("") == ""


SAMPLES = [
    "",
    "plain ascii",
    "  Mancozeb   \u06f8\u06f0%  ",
    "\u0642\u0627\u0631\u0686" + ZWNJ + ARABIC_KAF + "\u0634",
    ARABIC_KAF + TATWEEL + "\u0634\u0627\u0648\u0631\u0632" + ARABIC_YEH,
    "a" + ZWNJ + " " + ZWNJ + "b",
    "\u200f\u202bx\u202c",
    "\u0622\u0628 \u0627\u0628",
]


@pytest.mark.parametrize("sample", SAMPLES)
@pytest.mark.parametrize(
    "func", [normalize_letters, normalize_text, normalize_for_search, normalize_digits]
)
def test_normalizing_twice_changes_nothing(func, sample):
    once = func(sample)
    assert func(once) == once
