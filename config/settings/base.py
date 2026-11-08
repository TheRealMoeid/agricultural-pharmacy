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

# The store's own Telegram bot, which tells the staff about a new consultation
# request (D3, D42). Both values come from the environment; with either one
# empty nothing is sent and the request says so, which is what a development
# machine without a bot needs. The token is a secret: never in Git, a log line
# or a traceback (it is part of the Bot API address, so the address is never
# logged either).
TELEGRAM_BOT_TOKEN = env("DJANGO_TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_CHAT_ID = env("DJANGO_TELEGRAM_CHAT_ID", default="")

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
    "apps.articles",
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

# Static files: our own CSS and fonts live in static/ (see scripts/tailwind.py).
# collectstatic gathers them into STATIC_ROOT, which Nginx serves.
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Uploaded files (product photos and so on). Not in Git.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
