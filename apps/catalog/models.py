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
from django.db import models
from django.utils.text import slugify

from apps.core.text import normalize_for_search, normalize_text


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
