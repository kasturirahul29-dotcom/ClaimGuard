"""
Production settings.
All values MUST come from environment variables — never hardcoded.
"""
from decouple import config
from .base import *  # noqa: F401, F403

SECRET_KEY = config('SECRET_KEY')  # Required — will raise if missing

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# PostgreSQL — required in production
DATABASE_URL = config('DATABASE_URL')
import re  # noqa: E402
m = re.match(r'postgres(?:ql)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
if not m:
    raise ValueError(f"Cannot parse DATABASE_URL: {DATABASE_URL}")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': m.group(5),
        'USER': m.group(1),
        'PASSWORD': m.group(2),
        'HOST': m.group(3),
        'PORT': m.group(4),
        'CONN_MAX_AGE': 60,
    }
}

# CORS — restrict to the exact deployed frontend origin
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
