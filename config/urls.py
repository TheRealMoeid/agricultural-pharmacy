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
    path("consultation/", include("apps.consultations.urls")),
    path("", include("apps.pages.urls")),
]

if settings.DEBUG or getattr(settings, "SERVE_MEDIA_VIA_DJANGO", False):
    # Nginx serves the media files in the deployment this project plans for
    # (ARCHITECTURE.md, section 13). A host with no Nginx in front of it, such
    # as a Render free web service (D44), sets DJANGO_SERVE_MEDIA_VIA_DJANGO=true
    # so Django serves them instead -- slower, but media/ is ephemeral there
    # anyway (see README's "Staging on Render" section), so nothing more is lost.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
