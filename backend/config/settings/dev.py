"""
Development settings.
Reads .env from the backend/ directory via python-decouple.
"""
from decouple import config
from .base import *  # noqa: F401, F403

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-only-key-change-me-in-prod-xyz987')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ['*']

# ─── SQLite for local dev — no external DB needed ─────────────────────────────
# To switch to PostgreSQL, set DATABASE_URL=postgres://user:pass@host:5432/dbname
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    import re
    # Parse postgres://user:pass@host:port/dbname
    m = re.match(r'postgres(?:ql)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
    if m:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': m.group(5),
                'USER': m.group(1),
                'PASSWORD': m.group(2),
                'HOST': m.group(3),
                'PORT': m.group(4),
            }
        }
    else:
        raise ValueError(f"Cannot parse DATABASE_URL: {DATABASE_URL}")
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
        }
    }

# CORS — allow all in dev; lock down to specific origins in prod.py
CORS_ALLOW_ALL_ORIGINS = True
