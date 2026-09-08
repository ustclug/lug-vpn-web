#!/bin/sh

: ${TZ:=Asia/Shanghai}
ln -sfn /usr/share/zoneinfo/"$TZ" /etc/localtime
echo "$TZ" >/etc/timezone

python3 -c 'from app import app, db; context = app.app_context(); context.push(); db.create_all(); context.pop()'

exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers "${GUNICORN_WORKERS:-4}" \
    --access-logfile - \
    --error-logfile - \
    run:app
