"""The public consultation forms (D41) and the notification that follows a submission (D42)."""
import logging

from django.shortcuts import redirect, render

from .forms import ConsultationForm
from .models import ConsultationRequest
from .notifications import CRASHED, NotificationOutcome, send_consultation_notification
from .ratelimit import over_limit

logger = logging.getLogger(__name__)

Kind = ConsultationRequest.Kind


def _kind(request) -> str:
    """Which form: `?kind=farm_visit`, otherwise the question form. Always from the address."""
    wanted = request.GET.get("kind")
    return wanted if wanted in Kind.values else Kind.QUESTION


def _notify(consultation) -> None:
    """Tell the store about the saved request, and store what happened.

    The request is already in the database, so nothing about the send may cost
    the customer the thank-you page: a Telegram failure, or a notifier that
    breaks outright, is logged and written on the request (D33, D42), and the
    customer never learns about it.
    """
    try:
        outcome = send_consultation_notification(consultation)
    except Exception:  # noqa: BLE001 - a bug here must not cost the customer their page
        logger.exception("The notifier itself broke on request %s", consultation.pk)
        outcome = NotificationOutcome(ConsultationRequest.NotificationStatus.FAILED, CRASHED)
    consultation.notification_status = outcome.status
    consultation.notification_detail = outcome.detail
    # One extra UPDATE, of these two fields only: nothing else is re-saved.
    consultation.save(update_fields=["notification_status", "notification_detail"])


def consultation(request):
    kind = _kind(request)
    limited = False

    if request.method == "POST":
        if request.POST.get("website"):
            # A person never sees this field. Answer as if it worked, so the
            # bot learns nothing, and store nothing.
            return redirect("consultations:thank_you")
        if over_limit(request):
            limited = True
            form = ConsultationForm(kind=kind, initial=request.POST.dict())
        else:
            form = ConsultationForm(request.POST, kind=kind)
            if form.is_valid():
                saved = form.save()
                _notify(saved)
                return redirect("consultations:thank_you")
    else:
        form = ConsultationForm(kind=kind)

    return render(
        request,
        "consultations/form.html",
        {"form": form, "kind": kind, "limited": limited, "Kind": Kind},
        status=429 if limited else 200,
    )


def thank_you(request):
    return render(request, "consultations/thank_you.html")
