from django.urls import path

from . import views

app_name = "consultations"

urlpatterns = [
    path("", views.consultation, name="form"),
    path("thank-you/", views.thank_you, name="thank_you"),
]
