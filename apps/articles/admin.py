from django.contrib import admin
from django.db import models

from apps.core.forms import JalaliDateField

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    search_fields = ("title", "body")
    list_display = ("title", "season", "is_published", "published_date")
    list_filter = ("is_published", "season")
    list_editable = ("is_published",)
    readonly_fields = ("slug",)
    # The date is typed and shown in Jalali (D23); the field still stores a
    # plain Gregorian date, as the model defines it.
    formfield_overrides = {models.DateField: {"form_class": JalaliDateField}}

    fieldsets = (
        (None, {"fields": ("title", "slug", "season", "body")}),
        ("تصویر", {"fields": ("cover_image",)}),
        ("انتشار", {"fields": ("is_published", "published_date")}),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            return fieldsets
        # A new article has no slug yet, so there is nothing to show.
        trimmed = []
        for name, options in fieldsets:
            fields = tuple(f for f in options["fields"] if f != "slug")
            trimmed.append((name, {**options, "fields": fields}))
        return trimmed
