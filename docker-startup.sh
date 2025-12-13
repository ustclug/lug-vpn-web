#!/bin/sh

: ${TZ:=Asia/Shanghai}
ln -sfn /usr/share/zoneinfo/"$TZ" /etc/localtime
echo "$TZ" >/etc/timezone

cat >/srv/lugvpn-web/config/default.py <<EOF
SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://${MYSQL_USER:-root}:${MYSQL_PASSWORD:-radius}@${MYSQL_HOST:-mysql}/${MYSQL_DATABASE:-radius}?charset=${MYSQL_CHARSET:-utf8}'
DEBUG = ${DEBUG:-True}
SECRET_KEY = '${SECRET_KEY:-secret-key}'
SEND_FILE_MAX_AGE_DEFAULT = ${SEND_FILE_MAX_AGE_DEFAULT:-3600}

MAIL_ENABLE = ${MAIL_ENABLE:-False}
MAIL_SERVER = '${MAIL_SERVER:-mail}'
MAIL_PORT = ${MAIL_PORT:-25}
MAIL_USE_TLS = ${MAIL_TLS_ENABLE:-False}
MAIL_USE_SSL = ${MAIL_SSL_ENABLE:-False}
MAIL_USERNAME = '${MAIL_USERNAME}'
MAIL_PASSWORD = '${MAIL_PASSWORD}'
MAIL_DEFAULT_SENDER = '${MAIL_SENDER:-noreply@vpn.ustclug.org}'
ADMIN_MAIL = '${ADMIN_MAIL:-vpn@ustclug.org}'

BOOTSTRAP_SERVE_LOCAL = True

SQLALCHEMY_TRACK_MODIFICATIONS = False
EOF

# IMPORTANT:
# If Flask's SERVER_NAME is set, Flask will only accept requests whose Host header matches,
# otherwise it returns 404. Behind a reverse proxy (e.g., Caddy) the Host is usually your
# public domain, not "localhost".
#
# Therefore we ONLY set SERVER_NAME when the user explicitly provides it.
if [ -n "${SERVER_NAME:-}" ]; then
  echo "SERVER_NAME = '${SERVER_NAME}'" >>/srv/lugvpn-web/config/default.py
fi

# Wait for MySQL to be reachable before starting the app.
# This avoids a crash loop on first startup when the DB container is still initializing.
MYSQL_WAIT_HOST="${MYSQL_HOST:-mysql}"
MYSQL_WAIT_PORT="${MYSQL_PORT:-3306}"
MYSQL_WAIT_RETRIES="${MYSQL_WAIT_RETRIES:-60}"
MYSQL_WAIT_SLEEP="${MYSQL_WAIT_SLEEP:-1}"

echo "Waiting for MySQL at ${MYSQL_WAIT_HOST}:${MYSQL_WAIT_PORT} ..." >&2
python3 - <<'PY'
import os, socket, time, sys

host = os.environ.get("MYSQL_WAIT_HOST", "mysql")
port = int(os.environ.get("MYSQL_WAIT_PORT", "3306"))
retries = int(os.environ.get("MYSQL_WAIT_RETRIES", "60"))
sleep_s = float(os.environ.get("MYSQL_WAIT_SLEEP", "1"))

for i in range(retries):
    try:
        with socket.create_connection((host, port), timeout=1):
            print(f"MySQL is reachable at {host}:{port}", file=sys.stderr)
            raise SystemExit(0)
    except OSError:
        time.sleep(sleep_s)

print(f"Timed out waiting for MySQL at {host}:{port}", file=sys.stderr)
raise SystemExit(1)
PY

exec python3 run.py
