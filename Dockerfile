FROM smartentry/alpine:3.11

MAINTAINER Yifan Gao <docker@yfgao.com>

COPY docker $ASSETS_DIR

COPY . /srv/lugvpn-web

RUN smartentry.sh build

EXPOSE 5000/tcp

WORKDIR /srv/lugvpn-web

CMD ["python3", "run.py"]

