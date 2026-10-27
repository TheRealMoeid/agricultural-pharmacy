"""Content for the static pages: the experts and the FAQ.

Both are short lists that Habibollah or Moeid type in by hand, so the text is
cleaned on save the same way as in the catalog (Arabic yeh and kaf become
Persian, spaces are tidied), and a value that is only spaces is refused
instead of being saved as an empty string.
"""
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.fields import WebPImageField
from apps.core.text import normalize_letters, normalize_text


def _check_cleaned(instance, typed: dict, required: tuple) -> None:
    """Re-check text fields after they were cleaned.

    Cleaning can leave a "required" field empty (it was only spaces) or make
    a value longer than the column (compatibility characters expand). Both
    are reported as a normal form error. A field that was empty to begin with
    is left alone: the field's own check already reports that.
    """
    errors = {}
    for name, original in typed.items():
        value = getattr(instance, name)
        if name in required and not value:
            if original:
                errors[name] = "این فیلد را پر کنید."
            continue
        max_length = instance._meta.get_field(name).max_length
        if max_length and len(value) > max_length:
            errors[name] = "متن خیلی طولانی است."
    if errors:
        raise ValidationError(errors)


def expert_photo_path(instance: "Expert", filename: str) -> str:
    # `filename` is already a random name ending in .webp (see WebPImageField).
    return f"experts/{filename}"


class Expert(models.Model):
    """A person introduced on the experts page.

    Which lines appear for whom is decided by which fields are filled in, not
    by code: a field left empty is simply not shown. Rahmatollah has degree,
    experience and role; Habibollah has degree and specialty only (the client
    asked not to show his experience).
    """

    TEXT_FIELDS = ("name", "degree", "role", "experience", "specialty")
    REQUIRED_FIELDS = ("name", "degree")

    name = models.CharField("نام", max_length=120)
    degree = models.CharField("مدرک تحصیلی", max_length=200)
    role = models.CharField(
        "سمت",
        max_length=150,
        blank=True,
        help_text="اختیاری. اگر خالی بماند، نمایش داده نمی‌شود.",
    )
    experience = models.CharField(
        "سابقه",
        max_length=300,
        blank=True,
        help_text="اختیاری. اگر خالی بماند، نمایش داده نمی‌شود.",
    )
    specialty = models.CharField(
        "تخصص",
        max_length=200,
        blank=True,
        help_text="اختیاری. اگر خالی بماند، نمایش داده نمی‌شود.",
    )
    photo = WebPImageField(
        "عکس",
        upload_to=expert_photo_path,
        blank=True,
        max_side=480,
        quality=80,
        max_bytes=30_000,
        thumb_side=None,  # no list of small expert pictures, so no thumbnail
        help_text="تصویر jpg، png یا webp تا ۱۰ مگابایت. حجم آن خودکار کم و به webp تبدیل می‌شود.",
    )
    order = models.PositiveSmallIntegerField(
        "ترتیب نمایش",
        default=0,
        help_text="عدد کمتر یعنی بالاتر در صفحه.",
    )

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "کارشناس"
        verbose_name_plural = "کارشناسان"

    def __str__(self):
        return self.name

    def _normalize(self):
        for field in self.TEXT_FIELDS:
            setattr(self, field, normalize_text(getattr(self, field)))

    def clean(self):
        super().clean()
        typed = {field: getattr(self, field) for field in self.TEXT_FIELDS}
        self._normalize()
        _check_cleaned(self, typed, self.REQUIRED_FIELDS)

    def save(self, *args, **kwargs):
        self._normalize()
        super().save(*args, **kwargs)


class FaqItem(models.Model):
    """One question and its answer. The FAQ page exists only if there are any."""

    question = models.CharField("پرسش", max_length=300)
    answer = models.TextField("پاسخ")
    order = models.PositiveSmallIntegerField(
        "ترتیب نمایش",
        default=0,
        help_text="عدد کمتر یعنی بالاتر در فهرست.",
    )

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "پرسش متداول"
        verbose_name_plural = "پرسش‌های متداول"

    def __str__(self):
        return self.question

    def _normalize(self):
        self.question = normalize_text(self.question)
        # The answer can have several lines, so only the letters are unified
        # and the ends trimmed; line breaks inside are left as typed.
        self.answer = normalize_letters(self.answer).strip()

    def clean(self):
        super().clean()
        typed = {"question": self.question, "answer": self.answer}
        self._normalize()
        _check_cleaned(self, typed, ("question", "answer"))

    def save(self, *args, **kwargs):
        self._normalize()
        super().save(*args, **kwargs)
