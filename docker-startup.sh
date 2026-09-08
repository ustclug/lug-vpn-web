#!/bin/sh

: ${TZ:=Asia/Shanghai}
ln -sfn /usr/share/zoneinfo/"$TZ" /etc/localtime
echo "$TZ" >/etc/timezone

exec python3 run.py
