#!/bin/bash

: ${TZ:=Asia/Shanghai}
ln -sfn /usr/share/zoneinfo/"$TZ" /etc/localtime
echo "$TZ" >/etc/timezone

cat >/srv/lugvpn-web/config/default.py <<EOF
SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://${MYSQL_USER:-root}:${MYSQL_PASSWORD:-radius}@${MYSQL_HOST:-mysql}/${MYSQL_DATABASE:-radius}?charset=${MYSQL_CHARSET:-utf8}'
DEBUG = ${DEBUG:-True}
SECRET_KEY = '${SECRET_KEY:-secret-key}'
SERVER_NAME = '${SERVER_NAME:-localhost:5000}'

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

exec python3 run.py
