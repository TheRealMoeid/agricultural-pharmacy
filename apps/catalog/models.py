"""The reference tables of the catalog: product types, crops and pests.

All three are short lists of names that Habibollah (or Moeid) types in by hand,
so they share the same care about spelling:

- The name is cleaned on save (Arabic yeh and kaf become Persian, spaces are
  tidied) but never "searchified": what is shown stays correctly spelled.
- A comparison key (`name_key`, made by `normalize_for_search()`) is stored next
  to it and has to be unique. This stops "قارچ‌کش" and "قارچکش", or a name typed
  on an Arabic keyboard, from becoming two different entries that search could
  not tell apart.
- The slug is made from the name once, when the row is created, and then stays
  the same, so a link does not break if someone later fixes a spelling.
"""
from django.core.exceptions import ValidationError
from django.core.validators import validate_image_file_extension
from django.db import models
from django.utils.text import slugify

from apps.core.text import normalize_for_search, normalize_letters, normalize_text


class ReferenceItem(models.Model):
    """A named entry with a unique, normalized name and an automatic slug."""

    name = models.CharField("نام", max_length=100)
    slug = models.SlugField(
        "شناسه در نشانی",
        max_length=120,
        unique=True,
        allow_unicode=True,
        blank=True,
        help_text="خودکار از نام ساخته می‌شود و با تغییر نام عوض نمی‌شود.",
    )
    # Comparison key of the name. Set in _normalize(), never typed by a person.
    name_key = models.CharField(max_length=300, unique=True, blank=True, editable=False)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def _normalize(self):
        self.name = normalize_text(self.name)
        self.name_key = normalize_for_search(self.name)

    def _unique_slug(self) -> str:
        base = slugify(self.name, allow_unicode=True)[:110] or "item"
        others = type(self)._default_manager.exclude(pk=self.pk)
        slug, number = base, 1
        while others.filter(slug=slug).exists():
            number += 1
            slug = f"{base}-{number}"
        return slug

    def clean(self):
        super().clean()
        typed = self.name
        self._normalize()
        if len(self.name) > self._meta.get_field("name").max_length:
            raise ValidationError({"name": "نام خیلی طولانی است."})
        if not self.name_key:
            if typed:  # only spaces or invisible characters: the field check let it through
                raise ValidationError({"name": "نام را وارد کنید."})
            return  # truly empty: the field itself already reports it
        clash = (
            type(self)._default_manager.filter(name_key=self.name_key)
            .exclude(pk=self.pk)
            .first()
        )
        if clash:
            raise ValidationError({"name": f"«{clash.name}» از قبل ثبت شده است."})

    def validate_unique(self, exclude=None):
        # clean() already checks name_key, with a message a person can read.
        super().validate_unique(exclude={*(exclude or ()), "name_key"})

    def save(self, *args, **kwargs):
        self._normalize()
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)


class SearchTag(ReferenceItem):
    """A reference item that product search also matches by other names."""

    alternate_names = models.TextField(
        "نام‌های دیگر",
        blank=True,
        help_text="هر نام در یک خط. املاهای دیگر و نام‌های محلی که مشتری ممکن است جست‌وجو کند.",
    )

    class Meta:
        abstract = True

    def _normalize(self):
        super()._normalize()
        # One name per line, tidied, without repeats. A line that gives the same
        # search key as the name (or as an earlier line) adds nothing, so it goes.
        seen = {self.name_key}
        lines = []
        for line in self.alternate_names.splitlines():
            line = normalize_text(line)
            key = normalize_for_search(line)
            if key and key not in seen:
                seen.add(key)
                lines.append(line)
        self.alternate_names = "\n".join(lines)

    @property
    def alternate_name_list(self) -> list[str]:
        return [line.strip() for line in self.alternate_names.splitlines() if line.strip()]

    def search_keys(self) -> set[str]:
        """Every comparison key this entry answers to: its name and alternates."""
        keys = {normalize_for_search(self.name)}
        keys.update(normalize_for_search(name) for name in self.alternate_name_list)
        keys.discard("")
        return keys


class ProductType(ReferenceItem):
    """Fungicide, insecticide, herbicide, biological, booster fertilizer, ..."""

    order = models.PositiveSmallIntegerField(
        "ترتیب نمایش",
        default=0,
        help_text="عدد کمتر یعنی بالاتر در فهرست.",
    )

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "نوع محصول"
        verbose_name_plural = "انواع محصول"


class Crop(SearchTag):
    """A plant a product is used on: wheat, rapeseed, citrus, ..."""

    class Meta:
        ordering = ["name"]
        verbose_name = "گیاه"
        verbose_name_plural = "گیاهان"


class Pest(SearchTag):
    """What a product is used against: a pest, a disease or a weed."""

    class Meta:
        ordering = ["name"]
        verbose_name = "آفت / بیماری / علف هرز"
        verbose_name_plural = "آفات، بیماری‌ها و علف‌های هرز"


def product_photo_path(instance: "Product", filename: str) -> str:
    # The slug is not set yet on first save (it is assigned in save(), below
    # the file field), so uploads land in a flat folder named by id later if
    # needed. Keeping the path simple now; task 9 adds resizing and WebP
    # conversion and can reorganize storage at the same time.
    return f"products/{filename}"


class Product(models.Model):
    """A single product in the catalog.

    No price and no quantity (D7, confirmed requirements): Habibollah only
    flips `is_available`. Production and expiry dates are optional and, if
    both are empty, no date line is shown anywhere (D7) rather than hiding
    the product. Dates are entered and stored as Gregorian in this task;
    Jalali entry in the admin is task 8 (D23).

    Manufacturer, importer and country of origin are required plain-text
    fields, one per product (D6, confirmed in round 3: every product names
    the producer and importer companies and the country of origin).

    Whether products get a stored search key, the way the reference lists
    do, is decided in phase 2 together with `catalog/search.py` and the
    product list view, not here: a single key does not fit a search that has
    to match several fields and two related lists at once, and building that
    logic without the views next to it would be building ahead of use.
    """

    trade_name = models.CharField("نام تجاری", max_length=200)
    generic_name = models.CharField(
        "نام عمومی (ماده مؤثره)",
        max_length=200,
        help_text="نام ماده مؤثره، مثلاً «مانکوزب».",
    )
    slug = models.SlugField(
        "شناسه در نشانی",
        max_length=220,
        unique=True,
        allow_unicode=True,
        blank=True,
        help_text="خودکار از نام تجاری ساخته می‌شود و با تغییر نام عوض نمی‌شود.",
    )

    product_type = models.ForeignKey(
        ProductType,
        verbose_name="نوع محصول",
        on_delete=models.PROTECT,
        related_name="products",
    )

    usage = models.TextField("موارد مصرف", blank=True)
    dosage = models.CharField("میزان مصرف", max_length=200, blank=True)
    timing = models.CharField("زمان مصرف", max_length=200, blank=True)

    photo = models.ImageField(
        "عکس",
        upload_to=product_photo_path,
        blank=True,
        validators=[validate_image_file_extension],
        help_text="فایل باید تصویر باشد (jpg، png یا webp). تغییر اندازه و تبدیل به WebP در کار بعدی اضافه می‌شود.",
    )

    manufacturer = models.CharField("شرکت تولیدکننده", max_length=150)
    importer = models.CharField("شرکت واردکننده", max_length=150)
    country_of_origin = models.CharField("کشور سازنده", max_length=100)

    production_date = models.DateField(
        "تاریخ تولید",
        null=True,
        blank=True,
        help_text="به تقویم شمسی، مثلاً ۱۴۰۴/۰۱/۰۱. اگر خالی بماند، تاریخی روی صفحه محصول نمایش داده نمی‌شود.",
    )
    expiry_date = models.DateField(
        "تاریخ انقضا",
        null=True,
        blank=True,
        help_text="به تقویم شمسی، مثلاً ۱۴۰۴/۰۱/۰۱. اگر خالی بماند، تاریخی روی صفحه محصول نمایش داده نمی‌شود.",
    )

    is_available = models.BooleanField("موجود است", default=True)

    crops = models.ManyToManyField(Crop, verbose_name="گیاهان", blank=True, related_name="products")
    pests = models.ManyToManyField(
        Pest, verbose_name="آفات / بیماری‌ها / علف‌های هرز", blank=True, related_name="products"
    )

    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)

    class Meta:
        ordering = ["trade_name"]
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        constraints = [
            models.CheckConstraint(
                # A product with only an expiry date (no production date) is an
                # entry mistake worth catching early, not a real-world case:
                # D7 is about both dates being absent, not one of the two.
                condition=(
                    models.Q(expiry_date__isnull=True)
                    | models.Q(production_date__isnull=False)
                ),
                name="catalog_product_expiry_needs_production",
                violation_error_message="اگر تاریخ انقضا وارد شده، تاریخ تولید هم باید وارد شود.",
            ),
        ]

    def __str__(self):
        return self.trade_name

    def _normalize(self):
        self.trade_name = normalize_text(self.trade_name)
        self.generic_name = normalize_text(self.generic_name)
        self.manufacturer = normalize_text(self.manufacturer)
        self.importer = normalize_text(self.importer)
        self.country_of_origin = normalize_text(self.country_of_origin)
        self.dosage = normalize_text(self.dosage)
        self.timing = normalize_text(self.timing)
        # usage can be multi-line, so only the letters are unified; whitespace
        # and line breaks are left as typed (normalize_text() would flatten them).
        self.usage = normalize_letters(self.usage)

    def _unique_slug(self) -> str:
        base = slugify(self.trade_name, allow_unicode=True)[:210] or "product"
        others = Product._default_manager.exclude(pk=self.pk)
        slug, number = base, 1
        while others.filter(slug=slug).exists():
            number += 1
            slug = f"{base}-{number}"
        return slug

    def clean(self):
        super().clean()
        self._normalize()
        if self.production_date and self.expiry_date and self.expiry_date <= self.production_date:
            raise ValidationError({"expiry_date": "تاریخ انقضا باید بعد از تاریخ تولید باشد."})

    def save(self, *args, **kwargs):
        self._normalize()
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    @property
    def has_dates(self) -> bool:
        return bool(self.production_date or self.expiry_date)
