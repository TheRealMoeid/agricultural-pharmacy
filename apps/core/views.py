"""Tap counting for the call and message buttons (D16, resolved as D44).

Every call/WhatsApp/Telegram/Rubika button on the site points here instead
of straight at `tel:`/`wa.me`/`t.me`/the Rubika link. One GET: look up the
real destination from SiteSettings, log one ClickEvent, then redirect.

Routing through our own view, with a plain 302, works with no JavaScript at
all -- which matters on the old, weak-signal phones many visitors use, and
keeps the "no SPA, light or no JS" rule (D1) for this piece too. The
destination is always read from SiteSettings, never taken from the request,
so this cannot be used as an open redirect.

No personal data is stored: just which button, which page it was tapped
from (the `from` query parameter, filled in by the `click_url` template tag
in `apps/core/templatetags/clicks.py`, not the Referer header -- browsers
routinely strip or block that one), and when.
"""
from django.http import Http404
from django.http.response import HttpResponseRedirectBase
from django.shortcuts import redirect

from .models import ClickEvent, SiteSettings

Kind = ClickEvent.Kind

_DESTINATION = {
    Kind.CALL: "tel_url",
    Kind.WHATSAPP: "whatsapp_url",
    Kind.TELEGRAM: "telegram_url",
    Kind.RUBIKA: "rubika_url",
}

# Kept well under the field's own limit, so a long path never raises.
_PAGE_PATH_MAX_LENGTH = 255


class _TrackedRedirect(HttpResponseRedirectBase):
    """A plain 302 that also allows `tel:` -- Django's own redirect refuses it.

    The destination here is always one of SiteSettings' own derived URLs
    (tel:, wa.me, t.me, Rubika's link), built server-side, never taken from
    the request, so there is nothing "unsafe" about it to guard against.
    """

    status_code = 302
    allowed_schemes = [*HttpResponseRedirectBase.allowed_schemes, "tel"]


def track_click(request, kind):
    if kind not in Kind.values:
        raise Http404
    site = SiteSettings.load()
    destination = getattr(site, _DESTINATION[kind])
    if not destination:
        # A button only ever renders once its setting is filled in, so this
        # should not normally happen -- but a tap must still go somewhere.
        return redirect("pages:home")
    ClickEvent.objects.create(
        kind=kind,
        page_path=request.GET.get("from", "")[:_PAGE_PATH_MAX_LENGTH],
    )
    return _TrackedRedirect(destination)