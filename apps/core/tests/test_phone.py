import pytest
from django.core.exceptions import ValidationError

from apps.core.phone import (
    format_display,
    normalize_iran_mobile,
    to_international,
    validate_iran_mobile,
)

STORE = "09112747628"


@pytest.mark.parametrize(
    "typed",
    [
        "09112747628",
        "9112747628",
        "+989112747628",
        "989112747628",
        "00989112747628",
        "(+98)09112747628",  # the way it was first written down
        "+98 911 274 7628",
        "0911-274-7628",
        "0911 274 7628",
        "  09112747628  ",
        "\u06f0\u06f9\u06f1\u06f1\u06f2\u06f7\u06f4\u06f7\u06f6\u06f2\u06f8",  # Persian digits
        "\u0660\u0669\u0661\u0661\u0662\u0667\u0664\u0667\u0666\u0662\u0668",  # Arabic-Indic digits
    ],
)
def test_all_typings_of_the_same_number_normalize_alike(typed):
    assert normalize_iran_mobile(typed) == STORE


@pytest.mark.parametrize(
    "bad",
    [
        "",
        None,
        "abc",
        "0911274762",  # one digit short
        "091127476288",  # one digit too many
        "08112747628",  # does not start with 09
        "02112345678",  # a Tehran landline
        "+441234567890",
        "98",
        "0098",
    ],
)
def test_invalid_numbers_return_none(bad):
    assert normalize_iran_mobile(bad) is None


def test_to_international():
    assert to_international("09112747628") == "989112747628"
    assert to_international("+98 911 274 7628") == "989112747628"
    assert to_international("nonsense") is None


def test_format_display():
    assert format_display("09112747628") == "0911 274 7628"
    assert format_display("+989112747628") == "0911 274 7628"
    assert format_display("nonsense") == "nonsense"
    assert format_display(None) == ""


def test_validator_accepts_and_rejects():
    validate_iran_mobile("09112747628")
    with pytest.raises(ValidationError):
        validate_iran_mobile("12345")
