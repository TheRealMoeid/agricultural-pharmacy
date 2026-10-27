"""What a customer sends to the store: a question or a farm-visit request.

The record is the source of truth. A request is saved first and the
notification (SMS, Telegram, ...) is attempted afterwards, so a failed
notification never loses it; the outcome is stored on the request itself
(phase 3 fills it in, this task only gives it a place).

The phone number is personal data: it is shown to logged-in staff only, so it
is deliberately left out of __str__(), which ends up in logs and admin messages.
"""
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models

from apps.core.phone import normalize_iran_mobile, validate_iran_mobile
from apps.core.text import normalize_letters, normalize_text

MESSAGE_MAX_LENGTH = 2000

_REQUIRED = "این فیلد را پر کنید."
_TOO_LONG = "متن خیلی طولانی است."


class ConsultationRequest(models.Model):
    class Kind(models.TextChoices):
        QUESTION = "question", "پرسش از کارشناس"
        FARM_VISIT = "farm_visit", "درخواست بازدید از مزرعه"

    class Status(models.TextChoices):
        # The admin inbox sorts on "-status" so that new requests come first
        # ("new" sorts after "handled"). Keep that in mind before renaming.
        NEW = "new", "جدید"
        HANDLED = "handled", "رسیدگی شد"

    class NotificationStatus(models.TextChoices):
        NOT_ATTEMPTED = "not_attempted", "تلاش نشده"
        SENT = "sent", "ارسال شد"
        FAILED = "failed", "ناموفق"

    kind = models.CharField("نوع درخواست", max_length=20, choices=Kind.choices)
    name = models.CharField("نام", max_length=100)
    phone = models.CharField(
        "شماره تماس",
        max_length=25,
        validators=[validate_iran_mobile],
    )
    message = models.TextField(
        "متن پیام",
        blank=True,
        validators=[MaxLengthValidator(MESSAGE_MAX_LENGTH)],
        help_text="برای پرسش از کارشناس لازم است؛ برای بازدید از مزرعه اختیاری.",
    )
    crop = models.ForeignKey(
        "catalog.Crop",
        verbose_name="گیاه",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,  # a deleted crop must not delete the request
        related_name="consultation_requests",
    )
    village_or_address = models.CharField(
        "روستا یا نشانی مزرعه",
        max_length=255,
        blank=True,
        help_text="برای بازدید از مزرعه لازم است.",
    )

    status = models.CharField(
        "وضعیت",
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)

    notification_status = models.CharField(
        "نتیجه اطلاع‌رسانی",
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.NOT_ATTEMPTED,
    )
    notification_detail = models.TextField("توضیح اطلاع‌رسانی", blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "درخواست مشتری"
        verbose_name_plural = "درخواست‌های مشتریان"

    def __str__(self):
        # No phone number here, on purpose (see the module docstring).
        return f"{self.get_kind_display()} - {self.name}"

    def _normalize(self):
        self.name = normalize_text(self.name)
        self.village_or_address = normalize_text(self.village_or_address)
        self.phone = normalize_iran_mobile(self.phone) or self.phone
        # A customer's message can have several lines, so only the letters are
        # unified and the ends trimmed; line breaks inside are left as typed.
        self.message = normalize_letters(self.message).strip()

    def clean(self):
        super().clean()
        typed_name = self.name
        self._normalize()
        errors = {}
        if not self.name:
            if typed_name:  # only spaces: the field's own check let it through
                errors["name"] = _REQUIRED
        elif len(self.name) > self._meta.get_field("name").max_length:
            errors["name"] = _TOO_LONG
        if len(self.village_or_address) > self._meta.get_field("village_or_address").max_length:
            errors["village_or_address"] = _TOO_LONG
        if self.kind == self.Kind.QUESTION and not self.message:
            errors["message"] = "برای پرسش از کارشناس، متن پرسش را بنویسید."
        if self.kind == self.Kind.FARM_VISIT and not self.village_or_address:
            errors["village_or_address"] = "برای بازدید از مزرعه، روستا یا نشانی مزرعه را بنویسید."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self._normalize()
        super().save(*args, **kwargs)
