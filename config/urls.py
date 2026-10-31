"""Top-level URL routing.

Each app's URLs get included here as the apps are added. The admin lives on a
configurable path (DJANGO_ADMIN_URL) so it is not at the default /admin/ in
production.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("products/", include("apps.catalog.urls")),
    path("", include("apps.pages.urls")),
]

if settings.DEBUG:
    # In production Nginx serves the media files.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
