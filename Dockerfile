FROM library/python:3.9-alpine
WORKDIR /srv/lugvpn-web

COPY requirements.txt ./
RUN apk update && \
    apk add mariadb-connector-c tzdata && \
    apk add --virtual x-build-deps python3-dev build-base mariadb-dev && \
    pip3 install -r requirements.txt && \
    apk del --purge x-build-deps && \
    rm -rf /var/cache/apk/*

COPY . /srv/lugvpn-web
EXPOSE 5000/tcp
CMD ["./docker-startup.sh"]
