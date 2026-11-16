from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("experts/", views.experts, name="experts"),
    path("contact/", views.contact, name="contact"),
]