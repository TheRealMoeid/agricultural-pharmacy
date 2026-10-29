from django.shortcuts import render


def home(request):
    # A placeholder until the real home page is built (phase 4).
    return render(request, "pages/home.html")
