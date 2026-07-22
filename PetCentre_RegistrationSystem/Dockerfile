# --- Base image ---
FROM python:3.12-slim

# Prevents Python from writing .pyc files / buffering stdout — cleaner logs in Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# NOTE: previously this installed build-essential + libpq-dev to compile
# psycopg2 from source — that's what was slowly downloading ~86MB of
# compiler toolchain on every fresh build. Switching requirements.txt to
# psycopg2-binary (a pre-compiled wheel) removes the need for a C
# compiler entirely, so that step is no longer necessary.
#
# gdal-bin/libgdal-dev/libgeos-dev/libproj-dev ARE needed now that
# django.contrib.gis is enabled for PostGIS support (find-nearest-vets
# feature) — GeoDjango calls these native libraries directly via ctypes.
# This is the reliable way to get GDAL/GEOS working (vs. fighting
# Windows-native installs for local dev) — apt-get just works here.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libsqlite3-mod-spatialite \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (separate layer so `docker build` caches this
# unless requirements.txt actually changes — big speedup on rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Collect static files at build time (admin CSS/JS, DRF browsable API assets)
# Uses dummy values so this doesn't require real secrets during the build —
# collectstatic never touches the database or external services.
#
# --upload-unhashed-files is required even though nothing is actually
# uploaded anywhere: django-cloudinary-storage installs its OWN
# collectstatic command (it wins over Django's built-in one via
# INSTALLED_APPS command resolution), and that override's copy_file()
# silently no-ops — copies nothing, creates no STATIC_ROOT dir, exits 0
# — for any STATICFILES_STORAGE other than its own StaticCloudinaryStorage,
# UNLESS this flag is passed. Without it every static file 404s at
# runtime (admin CSS, pet_profiles' own CSS/JS, everything) with no
# build-time error to signal it.
RUN DJANGO_SECRET_KEY=build-time-placeholder \
    DB_PASSWORD=build-time-placeholder \
    python manage.py collectstatic --noinput --upload-unhashed-files

EXPOSE 8000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]