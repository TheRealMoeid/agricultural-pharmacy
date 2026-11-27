from django.urls import path

from . import views

app_name = "articles"

urlpatterns = [
    path("", views.article_list, name="article_list"),
    # <str:slug>, not <slug:slug>: article slugs keep Persian letters (see catalog/urls.py).
    path("<str:slug>/", views.article_detail, name="article_detail"),
]
