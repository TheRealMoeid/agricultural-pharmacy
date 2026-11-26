from django.shortcuts import render

from .models import Expert


def home(request):
    # No model queries of its own: every section links to a page that
    # already gathers its own data (products, experts, consultation, contact).
    return render(request, "pages/home.html")


def experts(request):
    qs = Expert.objects.order_by("order", "pk")
    return render(request, "pages/experts.html", {"experts": qs})


def contact(request):
    return render(request, "pages/contact.html")