# --- Base image ---
FROM python:3.12-slim

# Prevents Python from writing .pyc files / buffering stdout — cleaner logs in Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps needed to build psycopg2 and other native packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
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
RUN DJANGO_SECRET_KEY=build-time-placeholder \
    DB_PASSWORD=build-time-placeholder \
    python manage.py collectstatic --noinput

EXPOSE 8000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]