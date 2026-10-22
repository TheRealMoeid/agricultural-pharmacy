from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("اطلاعات فروشگاه", {"fields": ("store_name", "address", "working_hours")}),
        ("راه‌های ارتباطی", {"fields": ("phone", "telegram_username", "rubika_url")}),
        ("نقشه", {"fields": ("google_maps_url", "iranian_map_name", "iranian_map_url")}),
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
