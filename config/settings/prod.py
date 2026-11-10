"""Production and staging settings.

Everything secret or specific to the server comes from environment variables,
and a missing one stops the app at startup instead of falling back to a default.
"""
from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, env

DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

DATABASES = {"default": env.db("DATABASE_URL")}

# WhiteNoise serves static/ (compressed, hashed) with no Nginx in front of us
# (D44, the Render staging deploy, which has no separate web server). Right
# after SecurityMiddleware, as WhiteNoise's own docs ask for.
MIDDLEWARE = [
    MIDDLEWARE[0],
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]
# base.py never sets STORAGES, so Django's own default applies to "default"
# (plain FileSystemStorage for MEDIA_ROOT) except we swap "staticfiles".
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# D44: on a host with no Nginx (Render's free web services included), there is
# nobody else to serve /media/, so Django does it itself when this is on. Off
# by default because the real deployment plan (ARCHITECTURE.md, section 13)
# still has Nginx do this; a host without one sets DJANGO_SERVE_MEDIA_VIA_DJANGO=true.
SERVE_MEDIA_VIA_DJANGO = env.bool("DJANGO_SERVE_MEDIA_VIA_DJANGO", default=False)

# Nginx terminates HTTPS and tells Django through this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS makes browsers refuse plain HTTP for this long. Start low while HTTPS is
# being set up, then raise it to a year (31536000) once everything works.
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_CONTENT_TYPE_NOSNIFF = True

# No default here, so production cannot start on the public /admin/ path.
ADMIN_URL = env("DJANGO_ADMIN_URL")

# Behind Nginx every request seems to come from the proxy, so the form limit
# (apps/consultations/ratelimit.py) reads the visitor's address from this
# header. Nginx must overwrite it: proxy_set_header X-Real-IP $remote_addr;
CLIENT_IP_HEADER = env("DJANGO_CLIENT_IP_HEADER", default="HTTP_X_REAL_IP")
