#!/bin/sh
set -e

# When extra arguments are passed (e.g. Render's cron job dockerCommand),
# run that instead of the normal web-server boot sequence. Used by the
# scheduled notification-cleanup job, which just needs to run one
# management command and exit — not migrate+serve.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

echo "Waiting for database..."
python manage.py migrate --noinput

# Hosting platforms (Render, Railway, ...) inject the port to bind via
# $PORT; local docker-compose doesn't set it, so default to 8000 there.
echo "Starting Daphne (ASGI server) on 0.0.0.0:${PORT:-8000}..."
# Daphne's default --websocket_connect_timeout is 5s — the ChatConsumer's
# connect() handshake (JWT auth DB lookup + is_participant query against
# the remote Neon Postgres database) regularly takes longer than that
# under local Docker Desktop networking, so Daphne aborted the handshake
# before accept() finished, producing an endless WS reconnect loop.
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" --websocket_connect_timeout 30 djangojwt.asgi:application