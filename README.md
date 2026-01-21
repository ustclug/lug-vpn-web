## lug-vpn-web — WireGuard Management Portal

Document language: **English** / [中文](README-zh.md)

This repository provides a Flask-based web UI to manage WireGuard VPN clients. It includes an automated configuration generator and an SSE-based synchronization daemon to manage WireGuard peers.

---

## Components

- **`web`**: Flask application for user management and WireGuard peer configuration.
- **`mysql`**: Database to store user data and WireGuard peer information (dev profile only; use an external MySQL in production).
- **`caddy`**: Edge reverse proxy for HTTPS and serving the web UI.

---

## Requirements

- **Docker Engine + Docker Compose v2**
- **WireGuard** installed on the host (or a separate data plane host).
- **Python 3.10+** (if running the synchronization daemon on the host).

If you’re on an **arm64** host, set `DOCKER_PLATFORM=linux/amd64` in `.env` to force emulation if necessary.

---

## Configuration (`.env`)

Copy the example file and edit values:

```bash
cp .env.example .env
```

### Core Settings

- **`SECRET_KEY`**: A long, random string for Flask sessions.
- **`MYSQL_ROOT_PASSWORD`**, **`MYSQL_PASSWORD`**: Database credentials.
- **`SERVER_NAME`**: Leave **empty** unless you explicitly need it. If set, it must match the incoming **Host** header.

### WireGuard Settings (`WG_*`)

- **`WG_SERVER_ENDPOINT`**: Public address and port of the WireGuard server (e.g., `vpn.example.org:51820`).
- **`WG_SERVER_PRIVATE_KEY`**: The server's WireGuard private key (Base64 encoded Curve25519).
- **`WG_LISTEN_PORT`**: Port the WireGuard server listens on (default: `51820`).
- **`WG_SERVER_INTERFACE_IP`**: Internal IP of the WireGuard interface (default: `10.100.0.1/16`).
- **`WG_ADDRESS_POOL`**: CIDR range for client IPs (default: `10.100.0.0/16`).
- **`WG_DNS`**: DNS server(s) provided to clients (default: `1.1.1.1`).
- **`WG_ALLOWED_IPS`**: IPs routed through the VPN (default: `0.0.0.0/0, ::/0`).
- **`SSE_TOKEN`**: Shared secret for the synchronization daemon.

---

## Deployment

### 1) Prepare DNS and Caddy

Update `Caddyfile` with your domain and contact email. Point your domain's **A/AAAA** record to this host.

### 2) Start the Services

To run the web UI and database:

```bash
docker compose --profile core --profile dev up -d --build
```

### 3) WireGuard Synchronization

The web UI generates WireGuard configurations. To synchronize these with the actual WireGuard interface on the host, use the `wg_client_daemon.py` script:

```bash
# On the host where WireGuard is running
export SSE_TOKEN="your-secure-token"
export WG_API_URL="https://your-domain.com"
python3 scripts/wg_client_daemon.py --wg-dev wg0 --wg-config /etc/wireguard/wg0.conf
```

This daemon listens for updates via SSE and reloads the WireGuard interface automatically using `wg-quick`.

---

## Operations

### Start / Stop
```bash
docker compose --profile core --profile dev up -d
docker compose --profile core --profile dev down
```

### Logs
```bash
docker compose logs -f web
```

---

## Troubleshooting

### Web returns 404 behind a proxy
Check `SERVER_NAME` in `.env`. If it’s set and doesn’t match the incoming Host header, Flask will return 404. Recommended: leave `SERVER_NAME` empty.

### Invalid WireGuard Private Key
The `web` service will fail to start if `WG_SERVER_PRIVATE_KEY` is missing or invalid. Use `wg genkey` to generate a valid key.

### arm64 host: “no matching manifest for linux/arm64”
Set `DOCKER_PLATFORM=linux/amd64` in `.env` to force emulation.

---

## Development

Install [uv](https://docs.astral.sh/uv/) and run:

```bash
uv sync                      # Install dependencies
uv run pytest tests/ -v      # Run tests
uv run python run.py         # Start dev server (requires MySQL)
```

