"""Tests for JalaliDateField: typed Jalali text in, Gregorian date out, and back."""
import datetime

import pytest
from django import forms

from apps.core.forms import JalaliDateField

ARABIC_DIGIT_1404 = "\u0661\u0664\u0660\u0664"  # ۱۴۰۴ in Arabic-Indic digits
PERSIAN_1404 = "\u06f1\u06f4\u06f0\u06f4"  # ۱۴۰۴ in Persian digits


def field(**kwargs):
    return JalaliDateField(**kwargs)


# --- typed text -> Gregorian date ---------------------------------------------


def test_a_plain_ascii_date_is_parsed():
    assert field().clean("1404/07/02") == datetime.date(2025, 9, 24)


@pytest.mark.parametrize("separator", ["/", "-"])
def test_both_common_separators_work(separator):
    typed = separator.join(["1404", "01", "01"])
    assert field().clean(typed) == datetime.date(2025, 3, 21)


def test_persian_digits_are_accepted():
    assert field().clean(f"{PERSIAN_1404}/01/01") == datetime.date(2025, 3, 21)


def test_arabic_indic_digits_are_accepted():
    assert field().clean(f"{ARABIC_DIGIT_1404}/01/01") == datetime.date(2025, 3, 21)


def test_surrounding_whitespace_is_stripped():
    assert field().clean("  1402/06/31  ") is not None


def test_an_optional_empty_field_returns_none():
    assert field(required=False).clean("") is None


def test_a_required_empty_field_is_rejected():
    with pytest.raises(forms.ValidationError):
        field(required=True).clean("")


@pytest.mark.parametrize(
    "bad",
    [
        "not a date",
        "1404/01",  # only two parts
        "1404/01/01/01",  # too many parts
        "۱۴۰۴-۰۱",  # Persian digits, still too few parts
    ],
)
def test_the_wrong_shape_is_rejected_with_a_persian_message(bad):
    with pytest.raises(forms.ValidationError) as exc:
        field().clean(bad)
    assert "تاریخ را به صورت" in str(exc.value)


@pytest.mark.parametrize(
    "bad",
    [
        "1402/13/01",  # no 13th month
        "1402/01/32",  # no 32nd of any month
        "1402/12/30",  # 1402 is not a leap year: Esfand has 29 days
        "1402/07/31",  # Mehr only has 30 days
    ],
)
def test_a_calendar_date_that_does_not_exist_is_rejected(bad):
    with pytest.raises(forms.ValidationError) as exc:
        field().clean(bad)
    assert "وجود ندارد" in str(exc.value)


# --- stored Gregorian date -> Jalali text for display --------------------------


def test_prepare_value_shows_a_stored_date_in_jalali():
    assert field().prepare_value(datetime.date(2025, 3, 21)) == "1404/01/01"


def test_prepare_value_pads_single_digit_month_and_day():
    assert field().prepare_value(datetime.date(2025, 3, 21)) == "1404/01/01"
    assert field().prepare_value(datetime.date(2024, 12, 21)) == "1403/10/01"


def test_prepare_value_passes_through_none_and_strings():
    assert field().prepare_value(None) is None
    assert field().prepare_value("already a string") == "already a string"


def test_round_trip_through_the_field():
    f = field()
    typed = "1403/05/15"
    stored = f.clean(typed)
    assert f.prepare_value(stored) == typed
