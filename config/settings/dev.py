"""Local development settings."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

# A throwaway key, used only when nothing is set in the environment or .env.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="dev-only-insecure-key-do-not-use-in-production",
)

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# The default matches the PostgreSQL container that task 3 adds (compose.yml).
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://pharmacy:pharmacy@localhost:5432/pharmacy",
    )
}
