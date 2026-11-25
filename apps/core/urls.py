from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("<str:kind>/", views.track_click, name="track_click"),
]
