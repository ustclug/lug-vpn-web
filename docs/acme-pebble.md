## ACME testing: Pebble (`acme-test` profile)

This repo ships a **Pebble** ACME test server (compose profile `acme-test`) so you can validate the ACME flow **without real DNS / public ports**.

### Notes

- **Testing only**: Pebble is not a production CA.
- **Self-signed directory TLS**: Pebble’s ACME directory endpoint uses a self-signed HTTPS cert, so we pass `--insecure` for testing.
- **Challenge validation is skipped**: the compose service sets `PEBBLE_VA_ALWAYS_VALID=1`, so Pebble will skip HTTP-01/DNS-01/TLS-ALPN-01 validation. Domains can be arbitrary; `--standalone` is only used to let acme.sh complete the flow.

### Prereqs

- Docker Engine + Docker Compose v2 (`docker compose ...`)
- A `.env` file (copy from `.env.example`)
- `ACME_EMAIL` is recommended (any valid-looking email is fine for tests)

### 1) Start Pebble

```bash
docker compose --profile acme-test up -d pebble
```

### 2) Register an ACME account (against Pebble)

```bash
docker compose --profile acme --profile acme-test run --rm acme-sh \
  --register-account --server https://pebble:14000/dir --insecure \
  -m "$ACME_EMAIL"
```

### 3) Issue a test cert (against Pebble)

```bash
docker compose --profile acme --profile acme-test run --rm acme-sh \
  --issue --server https://pebble:14000/dir --insecure \
  -d vpn.test -d light.test \
  --standalone
```

### 4) Install into ocserv / light-server bind mounts

```bash
# ocserv
docker compose --profile acme --profile acme-test run --rm acme-sh \
  --install-cert --server https://pebble:14000/dir --insecure \
  -d vpn.test \
  --fullchain-file /target/ocserv-pki/public/server.crt \
  --key-file /target/ocserv-pki/private/server.key

# light-server
docker compose --profile acme --profile acme-test run --rm acme-sh \
  --install-cert --server https://pebble:14000/dir --insecure \
  -d light.test \
  --fullchain-file /target/light-ssl/server.crt \
  --key-file /target/light-ssl/server.key
```

If you actually started `vpn` / `proxy`, restart to load new certs:

```bash
docker compose --profile vpn restart ocserv
docker compose --profile proxy restart light-server
```

### 5) Stop Pebble

```bash
docker compose --profile acme-test down
```


