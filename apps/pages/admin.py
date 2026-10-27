from django.contrib import admin

from .models import Expert, FaqItem


@admin.register(Expert)
class ExpertAdmin(admin.ModelAdmin):
    search_fields = ("name", "degree", "role", "specialty")
    list_display = ("name", "degree", "role", "order")
    list_editable = ("order",)

    fieldsets = (
        (None, {"fields": ("name", "degree", "role")}),
        ("سابقه و تخصص", {"fields": ("experience", "specialty")}),
        ("عکس", {"fields": ("photo",)}),
        ("نمایش", {"fields": ("order",)}),
    )


@admin.register(FaqItem)
class FaqItemAdmin(admin.ModelAdmin):
    search_fields = ("question", "answer")
    list_display = ("question", "order")
    list_editable = ("order",)
