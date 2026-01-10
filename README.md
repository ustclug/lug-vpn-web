## lug-vpn-web — Deployment Guide (Docker Compose)

Document language: **English** / [中文](README-zh.md)

This repository ships a Flask web UI plus infrastructure services needed to operate a RADIUS-authenticated VPN/proxy stack. Everything is deployed with **`docker compose`** using **profiles**.

---

## Components and profiles

### `core` (control plane)

- **`caddy`**: edge reverse proxy for the web UI (**:80/:443**), configured by `Caddyfile`
- **`web`**: Flask app (this repo) on port **5000** (mapped to `${WEB_PORT}`)
- **`mysql`**: `mysql:5.7` (stores application + RADIUS data)
- **`freeradius`**: `ghcr.io/ustclug/docker-freeradius:nightly` (UDP **1812/1813/3799** published on the host)

### `vpn` (data plane)

- **`ocserv`**: OpenConnect server (runs with `network_mode: host`)

### `proxy` (data plane)

- **`light-server`**: HTTPS proxy (runs with `network_mode: host`)

### `acme` (tooling)

- **`acme-sh`**: containerized `acme.sh` used to issue/install certs for `ocserv` and `light-server`

### `acme-test` (optional)

- **`pebble`**: ACME test server (for CI/dev; not required for production deployment)

---

## Requirements

- **Docker Engine + Docker Compose v2** (`docker compose ...`)
- **Host networking support** for:
  - `ocserv` and `light-server` (profiles `vpn` / `proxy`)
- Designed for **Linux** (host networking semantics required).

If you’re on an **arm64** host, some images may be **amd64-only**. In that case, set `DOCKER_PLATFORM=linux/amd64` in `.env` to force emulation.

---

## Configuration (`.env`)

Copy the example file and edit values:

```bash
cp .env.example .env
```

Minimum required settings:

- **`SECRET_KEY`**: random, long string for Flask sessions
- **`MYSQL_ROOT_PASSWORD`**
- **`RADIUS_KEY` / `RADIUS_SECRET`**: must match across FreeRADIUS + clients

Data directory:

- **`DATA_ROOT`**: where bind-mounted data lives (defaults to `/srv/docker`)

Flask host validation (important):

- **`SERVER_NAME`**: leave **empty** unless you explicitly need it. If set, it must match the incoming **Host** header, otherwise Flask will return **404** (common when reverse-proxied).

---

## Deployment: single host (all-in-one)

This is the simplest topology: run `core` + `vpn` + `proxy` on one host.

### 1) Prepare DNS and Caddy

Edit `Caddyfile` to match your domain and contact email. The committed file reverse-proxies to `web:5000`:

```text
internet.zlix.tech {
	tls internet@ustc.global
	reverse_proxy web:5000
}
```

Point your domain’s **A/AAAA** record to this host. Caddy will obtain/renew certificates automatically.

### 2) Start the stack

```bash
docker compose --profile core --profile vpn --profile proxy up -d --build
```

### 3) Useful endpoints / ports

- **Web UI (direct)**: `http://<host>:${WEB_PORT:-5000}`
- **Web UI (via Caddy)**: `https://<your-domain>` (ports 80/443 on the host)
- **RADIUS (control plane)**: UDP `${RADIUS_AUTH_PORT:-1812}` / `${RADIUS_ACCT_PORT:-1813}` (optional CoA `${RADIUS_COA_PORT:-3799}`)
- **ocserv**: TCP/UDP `${OCSERV_TCP_PORT:-13806}` / `${OCSERV_UDP_PORT:-13806}` (host networking)
- **light-server**: HTTPS proxy on its configured port (default **29980**, host networking)

---

## Deployment: split control plane and data plane (recommended)

Operate the “stateful + admin” components centrally, and run VPN/proxy closer to users.

### Control plane host

Run web + DB + RADIUS:

```bash
docker compose --profile core up -d --build
```

Make sure these are reachable **from data plane hosts**:

- **RADIUS UDP**: `${RADIUS_AUTH_PORT:-1812}`, `${RADIUS_ACCT_PORT:-1813}` (and optionally `${RADIUS_COA_PORT:-3799}`)
- **Web**: 80/443 if you want public UI access (Caddy)

### Data plane host(s)

On each data plane host:

1) Copy `.env.example` to `.env`
2) Set:
   - `RADIUS_SERVER=<CONTROL_PLANE_IP_OR_DNS>`
   - `RADIUS_KEY` / `RADIUS_SECRET` to match the control plane
3) Start only data plane services:

```bash
docker compose --profile vpn --profile proxy up -d
```

---

## Certificates for `ocserv` and `light-server` (acme.sh)

`ocserv` and `light-server` read certs from bind-mounted paths:

- **ocserv**
  - `${DATA_ROOT}/ocserv/pki/public/server.crt`
  - `${DATA_ROOT}/ocserv/pki/private/server.key`
- **light-server**
  - `${DATA_ROOT}/light/ssl/server.crt`
  - `${DATA_ROOT}/light/ssl/server.key`

This repo provides an **`acme-sh` container** (profile `acme`) to issue and install certificates without installing certbot on the host.

### One-time: register an ACME account

Set `ACME_EMAIL` in `.env`, then:

```bash
docker compose --profile acme run --rm acme-sh \
  --register-account --server letsencrypt \
  -m "$ACME_EMAIL"
```

### ACME testing with Pebble (`acme-test`)

See `docs/acme-pebble.md`.

### Issue + install (recommended: DNS-01)

Because `caddy` binds **:80/:443**, DNS-01 is usually the simplest approach.

```bash
# 1) Issue (replace --dns <plugin> and credentials per your DNS provider)
docker compose --profile acme run --rm acme-sh \
  --issue --server letsencrypt --dns <your_dns_plugin> \
  -d vpn.zlix.tech -d light.zlix.tech

# 2) Install: ocserv
docker compose --profile acme run --rm acme-sh \
  --install-cert --server letsencrypt -d vpn.zlix.tech \
  --fullchain-file /target/ocserv-pki/public/server.crt \
  --key-file /target/ocserv-pki/private/server.key

chmod 400 "${DATA_ROOT}/ocserv/pki/private/server.key"
chmod 444 "${DATA_ROOT}/ocserv/pki/public/server.crt"
docker compose --profile vpn restart ocserv

# 3) Install: light-server
docker compose --profile acme run --rm acme-sh \
  --install-cert --server letsencrypt -d light.zlix.tech \
  --fullchain-file /target/light-ssl/server.crt \
  --key-file /target/light-ssl/server.key

chmod 400 "${DATA_ROOT}/light/ssl/server.key"
chmod 444 "${DATA_ROOT}/light/ssl/server.crt"
docker compose --profile proxy restart light-server
```

### Renewal automation

Run regularly via cron/systemd timer on the host:

```bash
docker compose --profile acme run --rm acme-sh --cron
```

After renewal, restart `ocserv` / `light-server` to load the new certs.

---

## FreeRADIUS database bootstrap (MySQL schema)

`ghcr.io/ustclug/docker-freeradius:nightly` can initialize its SQL schema via its **pre-run** hook:

- **When it runs**: only on the **first start of that container** (internal flag `HAVE_INITIALIZED=false`)
- **Conditions**:
  - `FREERADIUS_INIT_DATABASE_ENABLE != false`
  - `FREERADIUS_MYSQL_ADMIN_USERNAME` is set (non-empty)
- **What it does**: imports `/srv/tables.sql` and `/srv/user.sql` into MySQL using the admin credentials.

If you need to re-run bootstrap, **recreate** the `freeradius` container (the SQL uses `IF NOT EXISTS`, so repeated imports are generally safe).

---

## Operations

### Start / stop

```bash
docker compose --profile core up -d --build
docker compose --profile core down
```

### Pull updated images

```bash
docker compose --profile core --profile vpn --profile proxy pull
docker compose --profile core --profile vpn --profile proxy up -d
```

### Logs

```bash
docker compose logs -f --tail=200 web
docker compose logs -f --tail=200 freeradius
```

### Backups (recommended)

Back up `${DATA_ROOT}` directories you use, especially:

- `${DATA_ROOT}/mysql/data`
- `${DATA_ROOT}/ocserv/pki`
- `${DATA_ROOT}/light/ssl`
- `${DATA_ROOT}/acme.sh`

---

## Troubleshooting

### Web always returns 404 behind a proxy

Check `SERVER_NAME` in `.env`. If it’s set and doesn’t match the incoming Host header, Flask will return 404. Recommended: leave `SERVER_NAME` empty unless you explicitly need it.

### `network_mode: host` doesn’t work

This stack requires **Linux-style host networking** for profiles `vpn` / `proxy`.

### arm64 host: “no matching manifest for linux/arm64”

Set `DOCKER_PLATFORM=linux/amd64` in `.env` to force emulation.

### Where is `config/default.py`?

Configuration is now loaded directly from environment variables by `app/config.py`. See `.env.example` for all available options.

---

## Development

Install [uv](https://docs.astral.sh/uv/) and run:

```bash
uv sync                      # Install dependencies
uv run pytest tests/ -v      # Run tests
uv run python run.py         # Start dev server (requires MySQL)
```
