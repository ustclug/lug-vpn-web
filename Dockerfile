FROM python:3

MAINTAINER Yifan Gao "git@gaoyifan.com"

ENV CACHE_DIR="/etc/docker-lugvpn-apply"

ENV BUILD_SCRIPT="${CACHE_DIR}/build.sh" \
    TEMPLATES_DIR="${CACHE_DIR}/templates" \
    DEFAULT_ENV="${CACHE_DIR}/default_env"

COPY docker/assets $CACHE_DIR

COPY docker/entrypoint/entrypoint.sh /sbin/entrypoint.sh

COPY . /srv/lugvpn-apply

RUN /sbin/entrypoint.sh build

EXPOSE 5000/tcp

ENTRYPOINT ["/sbin/entrypoint.sh"]

WORKDIR /srv/lugvpn-apply

CMD ["/usr/local/bin/python", "run.py"]

