"""
Django settings for djangojwt project.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/
"""

import os
from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# Core / security
# ------------------------------------------------------------------
# SECURITY WARNING: keep the secret key used in production secret!
# Falls back to the original dev key only when DJANGO_SECRET_KEY is unset.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-c5!^5$9uvnd6f&w154v&ubiwu_#e*&=i=x&q)s6*v(1(5i1xc7',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

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
    'myapp',
]

MIDDLEWARE = [
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
# Registers myapp.User (role-aware) as the auth model for the whole
# project. Must be set before the first migration is ever applied.
AUTH_USER_MODEL = 'myapp.User'


# ------------------------------------------------------------------
# Database — PostgreSQL (+ PostGIS-ready)
# ------------------------------------------------------------------
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
#
# Configured entirely through environment variables so the same
# settings file works across local/dev/staging/production without
# code changes. Sensible local-dev defaults are provided as fallbacks.
#
# NOTE: the README specifies PostGIS for geospatial features (nearest
# pharmacy, donor proximity, rescue mapping). Once those features are
# built, switch ENGINE below to 'django.contrib.gis.db.backends.postgis'
# and add 'django.contrib.gis' to INSTALLED_APPS — the rest of this
# config (host/port/credentials) stays the same since PostGIS is a
# Postgres extension, not a different server.
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.environ.get('DB_NAME', 'petcentre'),
        'USER': os.environ.get('DB_USER', 'petcentre'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'petcentre_password'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
