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
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'rest_framework_simplejwt',
    'channels',
    'myapp',
    'chat',
    'core',
    'notifications',
    'pet_profiles',
    'corsheaders',
    'drf_spectacular',
]

# Lets the pet-owner login page's "Email or Phone" field authenticate
# by username OR email, since AUTH_USER_MODEL's USERNAME_FIELD is
# still 'username'. ModelBackend stays as a fallback for code paths
# that only ever pass a username (e.g. the DRF JWT login view).
AUTHENTICATION_BACKENDS = [
    'core.backends.UsernameOrEmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
        'DIRS': [BASE_DIR / 'templates'],
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
        # Switched from django.db.backends.postgresql to the PostGIS
        # backend — this is a drop-in replacement, same connection
        # params, same Neon host. It just adds spatial query support
        # (PointField, Distance, etc.) on top of the same Postgres
        # connection. Requires `CREATE EXTENSION postgis;` to have been
        # run once on the Neon database (via the Neon SQL Editor or
        # psql) — Neon supports this extension natively.
        'ENGINE': os.environ.get('DB_ENGINE', 'django.contrib.gis.db.backends.postgis'),
        'NAME': os.environ.get('DB_NAME', 'petcenter_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': _db_password,
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': os.environ.get('DB_SSLMODE', 'require'),
        },
    }
}

# ------------------------------------------------------------------
# GDAL/GEOS native library paths — ONLY needed for local `runserver`
# on Windows, where these libraries aren't on the system path the way
# they are inside the Docker image (which installs gdal-bin/libgeos
# via apt-get — see Dockerfile). Leave these unset entirely if running
# via Docker, or if GDAL/GEOS are already discoverable on your system.
# Set them in .env only if you hit "Could not find the GDAL/GEOS
# library" errors when running manage.py directly on Windows.
# Typical Windows paths after `pip install GDAL` via a wheel, e.g.:
#   GDAL_LIBRARY_PATH=C:\...\venv\Lib\site-packages\osgeo\gdal304.dll
#   GEOS_LIBRARY_PATH=C:\...\venv\Lib\site-packages\osgeo\geos_c.dll
if os.environ.get('GDAL_LIBRARY_PATH'):
    GDAL_LIBRARY_PATH = os.environ.get('GDAL_LIBRARY_PATH')
if os.environ.get('GEOS_LIBRARY_PATH'):
    GEOS_LIBRARY_PATH = os.environ.get('GEOS_LIBRARY_PATH')

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
# Uses SpatiaLite (SQLite's spatial extension) rather than plain SQLite,
# since VetProfile.location is a PostGIS PointField — plain SQLite has
# no spatial column types at all and fails with
# "AttributeError: 'DatabaseOperations' object has no attribute
# 'geo_db_type'" the moment migrations try to create that column.
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
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

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Where @login_required sends unauthenticated users for the
# session-based web pages (login page, dashboards, chat).
# Where @login_required sends unauthenticated users for session-based
# pages (chat, etc.). Points to the landing page's role picker, since
# there's no single generic login page — the person chooses pet owner
# / vet / admin from there.
LOGIN_URL = 'core:landing_page'

# --- Email (used for password-reset OTP codes) ---
# Defaults to printing emails to the console/terminal in dev, so OTP
# codes are visible without any real email provider configured. Set
# EMAIL_BACKEND and the SMTP_* vars in .env once you have a real
# provider (e.g. SendGrid, Mailgun, or plain SMTP).
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@petcentre.local')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').strip().lower() in ('true', '1', 'yes')

# --- pet_profiles app config ---
# Demo mode intentionally OFF — this project has a complete, real auth
# system already; the module's own fallback (auto-creating/reusing a
# shared fake account for anonymous visitors) would be a real security
# hole if left on here.
PET_PROFILES_DEMO_MODE = False
PET_PROFILE_CHATBOT_URL_NAME = 'core:chatbot'
# Points the "Upcoming" card at the real appointment system instead of
# a disconnected local one (pet_profiles' own Appointment model was
# removed entirely during integration).
PET_PROFILE_APPOINTMENT_URL_NAME = 'core:pet_owner_dashboard'

# ------------------------------------------------------------------
# Production hardening (only kicks in when DEBUG=False)
# ------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'True').strip().lower() in ('true', '1', 'yes')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True