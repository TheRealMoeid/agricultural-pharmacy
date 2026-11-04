"""The public consultation forms (D41)."""
from django.shortcuts import redirect, render

from .forms import ConsultationForm
from .models import ConsultationRequest
from .ratelimit import over_limit

Kind = ConsultationRequest.Kind


def _kind(request) -> str:
    """Which form: `?kind=farm_visit`, otherwise the question form. Always from the address."""
    wanted = request.GET.get("kind")
    return wanted if wanted in Kind.values else Kind.QUESTION


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
                form.save()
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
