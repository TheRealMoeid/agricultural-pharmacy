from django.contrib import admin
from django.db.models import Q

from apps.core.text import normalize_for_search, normalize_text

from .models import Crop, Pest, ProductType


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
