from django.contrib import admin
from django.db import models
from django.db.models import Q

from apps.core.forms import JalaliDateField
from apps.core.text import normalize_for_search, normalize_text

from .models import Crop, Pest, Product, ProductType


class ReferenceAdmin(admin.ModelAdmin):
    # Only here so Django shows the search box; the lookup itself is below.
    search_fields = ("name",)
    readonly_fields = ("slug",)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        # A new row has no slug yet, so there is nothing to show.
        return fields if obj else [f for f in fields if f != "slug"]

    def get_search_results(self, request, queryset, search_term):
        """Search the way customers will: typing style and ZWNJ do not matter.

        Every word has to match. A word is compared with the stored name key,
        and with the alternate names where the model has them.
        """
        for word in search_term.split():
            key = normalize_for_search(word)
            if not key:
                continue
            match = Q(name_key__contains=key)
            if hasattr(self.model, "alternate_names"):
                match |= Q(alternate_names__icontains=normalize_text(word))
            queryset = queryset.filter(match)
        return queryset, False


@admin.register(ProductType)
class ProductTypeAdmin(ReferenceAdmin):
    fields = ("name", "slug", "order")
    list_display = ("name", "order")
    list_editable = ("order",)


class SearchTagAdmin(ReferenceAdmin):
    fields = ("name", "slug", "alternate_names")
    list_display = ("name", "alternates")

    @admin.display(description="نام‌های دیگر")
    def alternates(self, obj):
        return "، ".join(obj.alternate_name_list)


@admin.register(Crop)
class CropAdmin(SearchTagAdmin):
    pass


@admin.register(Pest)
class PestAdmin(SearchTagAdmin):
    pass


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Plain icontains for now: Moeid and Habibollah both read and write
    # Persian correctly, so this box does not need the same typing-style
    # tolerance as the public search (built with search.py in phase 2).
    search_fields = ("trade_name", "generic_name", "manufacturer", "importer")
    list_display = ("trade_name", "generic_name", "product_type", "is_available")
    list_filter = ("product_type", "is_available")
    list_editable = ("is_available",)
    autocomplete_fields = ("product_type",)
    filter_horizontal = ("crops", "pests")
    readonly_fields = ("slug",)
    # Production and expiry dates are typed and shown in Jalali (D23); the
    # field itself still stores a plain Gregorian date, as the model defines it.
    formfield_overrides = {models.DateField: {"form_class": JalaliDateField}}

    fieldsets = (
        (None, {"fields": ("trade_name", "generic_name", "slug", "product_type", "photo")}),
        ("مصرف", {"fields": ("usage", "dosage", "timing")}),
        ("تولیدکننده", {"fields": ("manufacturer", "importer", "country_of_origin")}),
        ("تاریخ‌ها", {"fields": ("production_date", "expiry_date")}),
        ("جست‌وجو", {"fields": ("crops", "pests")}),
        ("وضعیت", {"fields": ("is_available",)}),
    )

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        return fields if obj else [f for f in fields if f != "slug"]

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            return fieldsets
        # Same reasoning as get_fields(): nothing to show for a new row.
        trimmed = []
        for name, options in fieldsets:
            fields = tuple(f for f in options["fields"] if f != "slug")
            trimmed.append((name, {**options, "fields": fields}))
        return trimmed
