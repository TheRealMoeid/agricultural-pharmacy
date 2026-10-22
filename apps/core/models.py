import re

from django.core.exceptions import ValidationError
from django.db import models

from .phone import (
    format_display,
    normalize_iran_mobile,
    to_international,
    validate_iran_mobile,
)

_TELEGRAM_USERNAME_RE = re.compile(r"^@?[A-Za-z][A-Za-z0-9_]{4,31}$")


def validate_telegram_username(value: str) -> None:
    if not _TELEGRAM_USERNAME_RE.match(value):
        raise ValidationError(
            "نام کاربری تلگرام معتبر نیست. باید ۵ تا ۳۲ نویسه از حروف انگلیسی، عدد و _ باشد.",
            code="invalid_telegram_username",
        )


class SiteSettings(models.Model):
    """The store's details and contact settings. There is only ever one row.

    Use SiteSettings.load() to get it. The fields start with the details the
    client has confirmed, so a fresh database already has a working number
    and address.
    """

    class NotificationChannel(models.TextChoices):
        NONE = "none", "هیچ‌کدام (فقط صندوق درخواست‌ها)"
        SMS = "sms", "پیامک"
        TELEGRAM = "telegram", "تلگرام"
        WHATSAPP = "whatsapp", "واتساپ"

    store_name = models.CharField(
        "نام فروشگاه",
        max_length=120,
        default="داروخانه گیاه‌پزشکی مهندس غیادی",
    )
    address = models.CharField(
        "نشانی",
        max_length=255,
        default="گلستان - گنبدکاووس - روستای آق‌آباد - انتهای روستا جنب نانوایی آزادپز",
    )
    working_hours = models.CharField(
        "ساعات کاری",
        max_length=200,
        default="شنبه تا پنجشنبه، ۸ تا ۱۳ و ۱۵ تا ۱۸ (جمعه‌ها تعطیل)",
    )

    phone = models.CharField(
        "شماره تماس",
        max_length=25,
        default="09112747628",
        validators=[validate_iran_mobile],
        help_text="شماره موبایل فروشگاه برای دکمه‌های تماس و واتساپ. نمونه: 09112747628",
    )
    telegram_username = models.CharField(
        "نام کاربری تلگرام",
        max_length=33,
        blank=True,
        validators=[validate_telegram_username],
        help_text="با یا بدون @. اگر خالی باشد، دکمه تلگرام نمایش داده نمی‌شود.",
    )
    rubika_url = models.URLField(
        "پیوند روبیکا",
        blank=True,
        help_text="پیوندی که روبیکا برای حساب فروشگاه می‌دهد. اگر خالی باشد، دکمه روبیکا نمایش داده نمی‌شود.",
    )

    google_maps_url = models.URLField("پیوند نقشه گوگل", blank=True)
    iranian_map_name = models.CharField(
        "نام برنامه نقشه ایرانی",
        max_length=50,
        blank=True,
        help_text="مثلاً نشان یا بلد. روی دکمه نمایش داده می‌شود.",
    )
    iranian_map_url = models.URLField("پیوند نقشه ایرانی", blank=True)

    notification_channel = models.CharField(
        "روش اطلاع‌رسانی درخواست‌ها",
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.NONE,
        help_text="درخواست‌های مشتریان همیشه در صندوق درخواست‌ها ذخیره می‌شوند.",
    )

    show_farm_visit_fee = models.BooleanField(
        "نمایش هزینه بازدید از مزرعه",
        default=False,
    )
    farm_visit_fee_text = models.CharField(
        "متن هزینه بازدید از مزرعه",
        max_length=200,
        blank=True,
        help_text="فقط وقتی نمایش داده می‌شود که گزینه بالا فعال باشد.",
    )

    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def __str__(self):
        return "تنظیمات سایت"

    @classmethod
    def load(cls) -> "SiteSettings":
        """Return the one settings row, creating it with the defaults if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def _normalize(self):
        self.phone = normalize_iran_mobile(self.phone) or self.phone
        self.telegram_username = self.telegram_username.strip().lstrip("@")
        self.store_name = self.store_name.strip()

    def clean(self):
        super().clean()
        self._normalize()

    def save(self, *args, **kwargs):
        # One row only: every save goes to the same record.
        self.pk = 1
        self._normalize()
        super().save(*args, **kwargs)

    @property
    def phone_display(self) -> str:
        return format_display(self.phone)

    @property
    def phone_international(self) -> str:
        return to_international(self.phone) or ""

    @property
    def tel_url(self) -> str:
        number = self.phone_international
        return f"tel:+{number}" if number else ""

    @property
    def whatsapp_url(self) -> str:
        number = self.phone_international
        return f"https://wa.me/{number}" if number else ""

    @property
    def telegram_url(self) -> str:
        return f"https://t.me/{self.telegram_username}" if self.telegram_username else ""

    @property
    def farm_visit_fee_visible(self) -> bool:
        return self.show_farm_visit_fee and bool(self.farm_visit_fee_text.strip())
