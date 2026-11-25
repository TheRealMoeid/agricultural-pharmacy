from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from .jalali import format_jalali_datetime
from .models import ClickEvent, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("اطلاعات فروشگاه", {"fields": ("store_name", "address", "working_hours")}),
        ("راه‌های ارتباطی", {"fields": ("phone", "telegram_username", "rubika_url")}),
        ("نقشه", {"fields": ("map_image", "google_maps_url", "iranian_map_name", "iranian_map_url")}),
        ("درخواست‌ها", {"fields": ("notification_channel",)}),
        ("هزینه بازدید از مزرعه", {"fields": ("show_farm_visit_fee", "farm_visit_fee_text")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # There is only one row, so skip the list and open it directly.
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        obj = SiteSettings.load()
        return redirect(reverse("admin:core_sitesettings_change", args=[obj.pk]))


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    """A read-only log, for measuring D16 ("increase sales" starts with calls).

    Nobody adds or edits these by hand; they are written only by
    core.views.track_click. Staff can look and filter, nothing more.
    """

    list_display = ("created_stamp", "kind", "page_path")
    list_filter = ("kind",)
    search_fields = ("page_path",)
    ordering = ("-created_at", "-pk")
    fields = ("kind", "page_path", "created_stamp")
    readonly_fields = ("kind", "page_path", "created_stamp")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="زمان", ordering="created_at")
    def created_stamp(self, obj):
        return format_jalali_datetime(obj.created_at)
