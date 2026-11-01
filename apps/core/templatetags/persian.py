"""Small display helpers for templates. `{% load persian %}`."""
from django import template

register = template.Library()

_TO_PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


@register.filter
def persian_digits(value):
    """12 -> ۱۲. Any other character is left as it is."""
    return str(value).translate(_TO_PERSIAN)


@register.filter
def jalali_date(value):
    """A stored Gregorian date -> "۱۴۰۴/۰۱/۰۱". None in, empty string out."""
    if value is None:
        return ""
    from apps.core.jalali import gregorian_to_jalali

    jy, jm, jd = gregorian_to_jalali(value)
    return persian_digits(f"{jy:04d}/{jm:02d}/{jd:02d}")
