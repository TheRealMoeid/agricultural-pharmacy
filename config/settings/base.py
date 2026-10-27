"""Settings shared by every environment.

Anything that differs between machines comes from environment variables (or a
local .env file) and is read through `env`. See .env.example.
"""
from pathlib import Path

import environ

# <repo>/config/settings/base.py -> parents[2] is the repository root.
BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env()

_env_file = BASE_DIR / ".env"
if _env_file.exists():
    env.read_env(_env_file)

# SECRET_KEY is set in dev.py (a throwaway default) and prod.py (required).

# The admin path, with a trailing slash. Production must set it to something
# that is not "admin/".
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Project apps are added here as they are created.
    "apps.core",
    "apps.catalog",
    "apps.pages",
    "apps.consultations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: PostgreSQL only. dev.py and prod.py set DATABASES from DATABASE_URL.

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Persian only (D20). Our own strings are written directly in templates and
# model labels, without gettext. USE_I18N stays on because Django's admin uses
# it to show its built-in Persian translation and right-to-left layout.
LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# Static files. STATICFILES_DIRS is added together with the static/ folder
# when the frontend work starts.
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Uploaded files (product photos and so on). Not in Git.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
