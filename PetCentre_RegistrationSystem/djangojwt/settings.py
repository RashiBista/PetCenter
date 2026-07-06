"""
Django settings for djangojwt project.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/
"""

import os
import sys
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# Core / security
# ------------------------------------------------------------------
# SECURITY: No hardcoded fallback secrets. In production these MUST be
# set via environment variables (.env locally, real secret storage in
# prod — e.g. AWS Secrets Manager, Doppler, Vault, platform env vars).
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').strip().lower() in ('true', '1', 'yes')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        # Convenience fallback ONLY for local dev when DEBUG=True and no
        # .env is set up yet. Never used in production because DEBUG
        # defaults to False and this branch is skipped below.
        SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-prod'
    else:
        raise RuntimeError(
            'DJANGO_SECRET_KEY environment variable is not set. '
            'Refusing to start with DEBUG=False and no secret key.'
        )

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'channels',
    'myapp',
    'chat',
    'corsheaders',
    'drf_spectacular',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    # Explicit default so every endpoint's access requirement is visible
    # in one place, and Swagger correctly shows lock icons per-view.
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# NOTE: was previously misspelled as SPECTULAR_SETTINGS, which meant
# drf-spectacular silently ignored this whole block and fell back to
# its own defaults (generic title, no description, version "").
SPECTACULAR_SETTINGS = {
    'TITLE': 'PetCentre API',
    'DESCRIPTION': 'API documentation for PetCentre',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # Adds a padlock icon per-endpoint in Swagger UI based on its
    # actual permission_classes, so locked vs open endpoints are
    # visually distinguishable at a glance.
    'SECURITY': [{'bearerAuth': []}],
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
}

ROOT_URLCONF = 'djangojwt.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'djangojwt.wsgi.application'

# ------------------------------------------------------------------
# Custom user model
# ------------------------------------------------------------------
AUTH_USER_MODEL = 'myapp.User'

# SECURITY: Wildcard CORS is fine for early local dev but should be
# tightened before any real deployment. Prefer an explicit allow-list
# driven by env vars so it's easy to change per-environment without
# touching code.
CORS_ALLOW_ALL_ORIGINS = os.environ.get('DJANGO_CORS_ALLOW_ALL', 'False').strip().lower() in ('true', '1', 'yes')
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        o.strip() for o in os.environ.get('DJANGO_CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()
    ]

# ------------------------------------------------------------------
# Database — PostgreSQL (+ PostGIS-ready)
# ------------------------------------------------------------------
# SECURITY: no hardcoded password fallback. DB_PASSWORD must come from
# the environment (.env locally, real secret storage in production).
# The app will fail fast at startup instead of silently connecting
# with a leaked default password.
_db_password = os.environ.get('DB_PASSWORD')
if not _db_password and 'test' not in sys.argv:
    raise RuntimeError(
        'DB_PASSWORD environment variable is not set. '
        'Set it in your .env file (see .env.example).'
    )

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.environ.get('DB_NAME', 'petcenter_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': _db_password,
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        # Neon (and most managed Postgres providers) require SSL.
        # Defaults to 'require' so this is safe even if DB_SSLMODE is
        # unset — plain localhost Postgres in dev generally accepts
        # sslmode=require too (it just negotiates SSL if available),
        # but override to 'disable' locally if that ever causes issues.
        'OPTIONS': {
            'sslmode': os.environ.get('DB_SSLMODE', 'require'),
        },
    }
}

ASGI_APPLICATION = 'djangojwt.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(
                os.environ.get('REDIS_HOST', '127.0.0.1'),
                int(os.environ.get('REDIS_PORT', '6379')),
            )],
        },
    },
}

# Allow tests to run without a PostgreSQL server / without DB_PASSWORD set.
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Production hardening (only kicks in when DEBUG=False)
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'True').strip().lower() in ('true', '1', 'yes')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True