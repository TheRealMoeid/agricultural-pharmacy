from django.shortcuts import render

from .models import Expert


def home(request):
    return render(request, "pages/home.html")


def experts(request):
    qs = Expert.objects.order_by("order", "pk")
    return render(request, "pages/experts.html", {"experts": qs})


def contact(request):
    return render(request, "pages/contact.html")