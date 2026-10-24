"""Form fields shared across admin screens.

JalaliDateField is the one piece: a text field that lets a person type a date
in the Jalali calendar and stores/reads it as the Gregorian date a model's
DateField actually holds (D23). The conversion itself lives in jalali.py;
this file is only about turning typed text into a date and a date back into
text.
"""
import datetime
import re

from django import forms
from django.core.exceptions import ValidationError

from .jalali import gregorian_to_jalali, jalali_to_gregorian

_PARTS_RE = re.compile(r"[/\-\s]+")

_BAD_FORMAT = "تاریخ را به صورت ۱۴۰۴/۰۱/۰۱ وارد کنید."
_BAD_DATE = "این تاریخ در تقویم شمسی وجود ندارد."


class JalaliDateWidget(forms.TextInput):
    input_type = "text"

    def __init__(self, attrs=None):
        base = {"placeholder": "۱۴۰۴/۰۱/۰۱", "dir": "ltr", "class": "vTextField"}
        if attrs:
            base.update(attrs)
        super().__init__(attrs=base)


class JalaliDateField(forms.CharField):
    """A model DateField's form field, replaced to read and write Jalali.

    to_python() parses the typed text (Persian, Arabic-Indic or ASCII digits,
    "/" or "-" as the separator) and returns a Gregorian `datetime.date`,
    which is what a plain DateField expects from here on -- validation,
    required-ness and saving all work exactly as they would for Django's own
    DateField. Persian and Arabic-Indic digits need no separate conversion
    here: Python's own int() already reads them by their Unicode numeric
    value (`int("\u06f1\u06f4\u06f0\u06f4") == 1404`), so str.isdigit() and
    int() below handle all three digit systems as they are.
    prepare_value() does the reverse for display: a stored Gregorian date
    becomes the Jalali text the field shows.
    """

    widget = JalaliDateWidget

    def __init__(self, **kwargs):
        kwargs.setdefault("strip", True)
        super().__init__(**kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return None
        parts = _PARTS_RE.split(value.strip())
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValidationError(_BAD_FORMAT, code="invalid_jalali_format")
        jy, jm, jd = (int(p) for p in parts)
        try:
            return jalali_to_gregorian(jy, jm, jd)
        except ValueError:
            raise ValidationError(_BAD_DATE, code="invalid_jalali_date") from None

    def prepare_value(self, value):
        if isinstance(value, datetime.date):
            jy, jm, jd = gregorian_to_jalali(value)
            return f"{jy:04d}/{jm:02d}/{jd:02d}"
        return value
