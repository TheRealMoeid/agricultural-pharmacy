"""Small display helpers for templates. `{% load persian %}`."""
from django import template

register = template.Library()

_TO_PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


@register.filter
def persian_digits(value):
    """12 -> ۱۲. Any other character is left as it is."""
    return str(value).translate(_TO_PERSIAN)
