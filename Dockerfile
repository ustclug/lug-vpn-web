# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.13-alpine

# Install system dependencies for mysqlclient
RUN apk add --no-cache \
    mariadb-connector-c \
    tzdata \
    && apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    mariadb-dev \
    pkgconf

WORKDIR /srv/lugvpn-web

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (without dev dependencies)
RUN uv sync --frozen --no-dev \
    && apk del .build-deps

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY run.py gunicorn.conf.py ./

EXPOSE 5000/tcp

# Use Gunicorn as production WSGI server
CMD ["uv", "run", "gunicorn", "-c", "gunicorn.conf.py", "app:app"]
