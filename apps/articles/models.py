"""Seasonal articles written by the experts.

The articles section is built from the start but stays out of the navigation
until the first article is published (D11). The public pages (phase 4) decide
that with `Article.objects.published().exists()`.

The body is plain text: a blank line starts a new paragraph. There is no
Markdown or HTML to learn or to get wrong, and nothing to sanitize.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.core.fields import WebPImageField
from apps.core.text import normalize_letters, normalize_text

_REQUIRED = "این فیلد را پر کنید."
_TOO_LONG = "متن خیلی طولانی است."


def article_image_path(instance: "Article", filename: str) -> str:
    # `filename` is already a random name ending in .webp (see WebPImageField).
    return f"articles/{filename}"


class ArticleQuerySet(models.QuerySet):
    def published(self):
        """Published articles, newest first. Drafts never appear here."""
        return self.filter(is_published=True).order_by("-published_date", "-pk")


class Article(models.Model):
    class Season(models.TextChoices):
        SPRING = "spring", "بهار"
        SUMMER = "summer", "تابستان"
        AUTUMN = "autumn", "پاییز"
        WINTER = "winter", "زمستان"

    title = models.CharField("عنوان", max_length=200)
    slug = models.SlugField(
        "شناسه در نشانی",
        max_length=220,
        unique=True,
        allow_unicode=True,
        blank=True,
        help_text="خودکار از عنوان ساخته می‌شود و با تغییر عنوان عوض نمی‌شود.",
    )
    season = models.CharField("فصل", max_length=10, choices=Season.choices)
    body = models.TextField(
        "متن مقاله",
        help_text="بین هر دو بند یک خط خالی بگذارید.",
    )
    cover_image = WebPImageField(
        "تصویر مقاله",
        upload_to=article_image_path,
        blank=True,
        max_side=800,
        quality=80,
        max_bytes=50_000,
        thumb_side=320,
        thumb_max_bytes=12_000,
        help_text="تصویر jpg، png یا webp تا ۱۰ مگابایت. حجم آن خودکار کم و به webp تبدیل می‌شود و یک نسخه کوچک برای فهرست‌ها ساخته می‌شود.",
    )
    is_published = models.BooleanField(
        "منتشر شده",
        default=False,
        help_text="تا وقتی تیک نخورده، مقاله فقط در بخش مدیریت دیده می‌شود.",
    )
    published_date = models.DateField(
        "تاریخ انتشار",
        null=True,
        blank=True,
        help_text="به تقویم شمسی، مثلاً ۱۴۰۵/۰۸/۰۵. اگر مقاله منتشر شود و این خالی بماند، تاریخ امروز ثبت می‌شود.",
    )

    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)

    objects = ArticleQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "مقاله"
        verbose_name_plural = "مقالات"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_published=False) | models.Q(published_date__isnull=False),
                name="articles_article_published_needs_date",
                violation_error_message="مقاله منتشرشده باید تاریخ انتشار داشته باشد.",
            ),
        ]

    def __str__(self):
        return self.title

    def _normalize(self):
        self.title = normalize_text(self.title)
        # The body has several paragraphs, so only the letters are unified and
        # the ends trimmed; line breaks inside are left as typed.
        self.body = normalize_letters(self.body).strip()

    def _fill_published_date(self):
        if self.is_published and self.published_date is None:
            self.published_date = timezone.localdate()  # store time zone, not UTC

    def _unique_slug(self) -> str:
        base = slugify(self.title, allow_unicode=True)[:210] or "article"
        others = Article._default_manager.exclude(pk=self.pk)
        slug, number = base, 1
        while others.filter(slug=slug).exists():
            number += 1
            slug = f"{base}-{number}"
        return slug

    def clean(self):
        super().clean()
        typed_title, typed_body = self.title, self.body
        self._normalize()
        errors = {}
        if not self.title:
            if typed_title:  # only spaces: the field's own check let it through
                errors["title"] = _REQUIRED
        elif len(self.title) > self._meta.get_field("title").max_length:
            errors["title"] = _TOO_LONG
        if not self.body and typed_body:
            errors["body"] = _REQUIRED
        if errors:
            raise ValidationError(errors)
        self._fill_published_date()

    def save(self, *args, **kwargs):
        self._normalize()
        self._fill_published_date()
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)
