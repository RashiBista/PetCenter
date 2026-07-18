#!/bin/sh
set -e

echo "Waiting for database..."
python manage.py migrate --noinput

echo "Starting Daphne (ASGI server) on 0.0.0.0:8000..."
# Daphne's default --websocket_connect_timeout is 5s — the ChatConsumer's
# connect() handshake (JWT auth DB lookup + is_participant query against
# the remote Neon Postgres database) regularly takes longer than that
# under local Docker Desktop networking, so Daphne aborted the handshake
# before accept() finished, producing an endless WS reconnect loop.
exec daphne -b 0.0.0.0 -p 8000 --websocket_connect_timeout 30 djangojwt.asgi:application