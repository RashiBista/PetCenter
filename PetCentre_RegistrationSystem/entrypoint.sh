#!/bin/sh
set -e

echo "Waiting for database..."
python manage.py migrate --noinput

echo "Starting Daphne (ASGI server) on 0.0.0.0:8000..."
exec daphne -b 0.0.0.0 -p 8000 djangojwt.asgi:application