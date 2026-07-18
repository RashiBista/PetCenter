#!/bin/sh
set -e

# Neon's shared-proxy routing requires the endpoint ID be identified via
# TLS SNI on the outbound ClientHello. pgbouncer 1.25's outbound TLS
# client doesn't set that, and its own [databases] config format has no
# supported way to attach the `options=endpoint=...` connection
# parameter that's the documented fallback for clients without SNI
# support (see https://neon.tech/docs/connect/connectivity-issues) — so
# this writes the config by hand instead of using the image's built-in
# DATABASE_URL-driven generator, using Neon's OTHER documented
# workaround: embedding the endpoint ID into the password field as
# `endpoint=<id>;<password>`. Neon then authenticates with the plain
# `password` method instead of scram-sha-256 for this hop — the
# connection stays TLS-encrypted throughout, so this is not a
# meaningful security downgrade for a local dev database connection.
ENDPOINT_ID=$(echo "$DB_HOST" | cut -d. -f1)

cat > /tmp/pgbouncer.ini <<EOF
[databases]
${DB_NAME} = host=${DB_HOST} port=${DB_PORT} dbname=${DB_NAME} user=${DB_USER} password=endpoint=${ENDPOINT_ID};${DB_PASSWORD}

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
# any: accepts any username with no password/lookup at all (trust still
# requires the user to exist in auth_file, which is empty here). This
# listener is only reachable from other containers on the compose
# network — no host port is published for it, and the app container is
# the only real client — so there's no exposure to gate with a second
# password on top of the one already required to reach this network.
auth_type = any
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 100
default_pool_size = 10
min_pool_size = 2
server_tls_sslmode = require
admin_users = ${DB_USER}
ignore_startup_parameters = extra_float_digits
EOF

echo "Starting pgbouncer, proxying ${DB_NAME} @ ${DB_HOST} (endpoint=${ENDPOINT_ID})..."
exec /usr/bin/pgbouncer /tmp/pgbouncer.ini
