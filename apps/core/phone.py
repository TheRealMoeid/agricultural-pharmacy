"""Iranian mobile number helpers.

The store's number is typed in all sorts of ways: with Persian digits, with
spaces, with +98, with 0098, or even "(+98)09112747628". Everything is turned
into one canonical form, 09XXXXXXXXX, and the other forms are derived from it.

Only mobile numbers are supported (they start with 09). If the store ever
needs a landline number on the site, this is the place to extend.
"""
import re

from django.core.exceptions import ValidationError

from .text import normalize_digits

_NATIONAL_BODY_RE = re.compile(r"9\d{9}")


def normalize_iran_mobile(value: str | None) -> str | None:
    """Return the number as 09XXXXXXXXX, or None if it is not a valid mobile number."""
    digits = re.sub(r"\D", "", normalize_digits(value))
    if digits.startswith("0098"):
        digits = digits[4:]
    elif digits.startswith("98"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = digits[1:]
    if not _NATIONAL_BODY_RE.fullmatch(digits):
        return None
    return "0" + digits


def to_international(value: str | None) -> str | None:
    """09112747628 -> 989112747628 (the form wa.me links want)."""
    national = normalize_iran_mobile(value)
    return "98" + national[1:] if national else None


def format_display(value: str | None) -> str:
    """09112747628 -> "0911 274 7628". Returns the input unchanged if it is not valid."""
    national = normalize_iran_mobile(value)
    if not national:
        return value or ""
    return f"{national[:4]} {national[4:7]} {national[7:]}"


def validate_iran_mobile(value: str) -> None:
    if normalize_iran_mobile(value) is None:
        raise ValidationError(
            "شماره موبایل معتبر نیست. نمونه: 09112747628",
            code="invalid_mobile",
        )
