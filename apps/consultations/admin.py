from django.contrib import admin, messages
from django.db.models import Q
from django.utils import timezone
from django.utils.html import format_html

from apps.core.jalali import gregorian_to_jalali
from apps.core.phone import format_display, to_international
from apps.core.text import normalize_digits, normalize_letters, normalize_text

from .models import ConsultationRequest

Status = ConsultationRequest.Status


def format_jalali_datetime(value) -> str:
    """A stored datetime as "1405/01/01 15:30": Jalali date, store-local time."""
    local = timezone.localtime(value)
    jy, jm, jd = gregorian_to_jalali(local.date())
    return f"{jy:04d}/{jm:02d}/{jd:02d} {local:%H:%M}"


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    """The staff inbox.

    Customers' details are read-only here: the only thing staff change is the
    status. Requests come from the public forms, so there is no "add".
    """

    list_display = ("created_stamp", "name", "kind", "phone_link", "status")
    list_display_links = ("name",)
    list_filter = ("status", "kind")
    # "new" sorts after "handled", so "-status" puts open requests on top.
    ordering = ("-status", "-created_at", "-pk")
    search_fields = ("name", "phone", "village_or_address", "message")
    actions = ("mark_handled", "mark_new")

    fieldsets = (
        (
            "درخواست",
            {"fields": ("kind", "name", "phone_link", "crop", "village_or_address", "message")},
        ),
        ("پیگیری", {"fields": ("status",)}),
        (
            "اطلاعات ثبت",
            {"fields": ("created_stamp", "notification_status", "notification_detail")},
        ),
    )
    readonly_fields = (
        "kind",
        "name",
        "phone_link",
        "crop",
        "village_or_address",
        "message",
        "created_stamp",
        "notification_status",
        "notification_detail",
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="زمان ثبت", ordering="created_at")
    def created_stamp(self, obj):
        return format_jalali_datetime(obj.created_at)

    @admin.display(description="شماره تماس")
    def phone_link(self, obj):
        number = to_international(obj.phone)
        if not number:
            return obj.phone
        # One tap on a phone starts the call.
        return format_html('<a href="tel:+{}" dir="ltr">{}</a>', number, format_display(obj.phone))

    def get_search_results(self, request, queryset, search_term):
        """Every word has to match somewhere; digits and letters are typed any way.

        Phone numbers are stored with ASCII digits, so a number typed with
        Persian digits is converted before comparing. Text is stored cleaned,
        so the typed word is cleaned the same way.
        """
        for word in search_term.split():
            match = Q(phone__icontains=normalize_digits(word))
            clean = normalize_text(word)
            if clean:
                match |= Q(name__icontains=clean) | Q(village_or_address__icontains=clean)
            letters = normalize_letters(word)
            if letters:
                match |= Q(message__icontains=letters)
            queryset = queryset.filter(match)
        return queryset, False

    @admin.action(description="علامت‌گذاری به‌عنوان «رسیدگی شد»", permissions=["change"])
    def mark_handled(self, request, queryset):
        count = queryset.filter(status=Status.NEW).update(status=Status.HANDLED)
        self.message_user(request, f"{count} درخواست «رسیدگی شد» شد.", messages.SUCCESS)

    @admin.action(description="برگرداندن به «جدید»", permissions=["change"])
    def mark_new(self, request, queryset):
        count = queryset.filter(status=Status.HANDLED).update(status=Status.NEW)
        self.message_user(request, f"{count} درخواست به «جدید» برگشت.", messages.SUCCESS)
