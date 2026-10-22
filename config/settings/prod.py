"""Production and staging settings.

Everything secret or specific to the server comes from environment variables,
and a missing one stops the app at startup instead of falling back to a default.
"""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

DATABASES = {"default": env.db("DATABASE_URL")}

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
