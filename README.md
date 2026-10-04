# VATComply

Rust API for VAT validation, ECB exchange rates, VAT rates, and IP geolocation. Paths, query parameters, status codes, and JSON bodies match `https://api.vatcomply.com`. The cut-over is in [`deploy/PRODUCTION.md`](deploy/PRODUCTION.md).

A release binary serves `/rates` from an embedded ECB snapshot when disk and network are both unavailable. VIES then returns its documented unavailable error.

## Self-hosting

### Docker

```shell
docker run --rm -p 8000:8000 -v vatcomply-data:/data ghcr.io/madisvain/vatcomply
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/rates
```

Build the image yourself from this directory:

```shell
docker build -t vatcomply .
docker run --rm -p 8000:8000 vatcomply
```

The image is `FROM scratch`, runs as UID 65532, and declares `DATA_DIR=/data`. A root-owned volume logs a snapshot write error and still serves the embedded rates. To persist refreshes:

```shell
docker run --rm -v vatcomply-data:/data alpine chown 65532:65532 /data
```

`HEALTHCHECK` runs `vatcomply healthcheck` (a TCP GET of `/healthz`). There is no shell and no curl in the image.

### Compose

From the repository root:

```shell
docker compose -f deploy/docker-compose.yml up -d
```

The compose file publishes port 8000, sets a 2 request/second limit with burst 4, and mounts a named volume at `/data`.

### Binary and systemd

Install a release binary at `/usr/local/bin/vatcomply` (GitHub Releases via cargo-dist, or `cargo build --release` in this directory). Then:

```shell
sudo cp deploy/vatcomply.service /etc/systemd/system/vatcomply.service
sudo systemctl daemon-reload
sudo systemctl enable --now vatcomply
```

The unit uses `DynamicUser=yes`, `StateDirectory=vatcomply`, `ProtectSystem=strict`, `NoNewPrivileges=yes`, and `Restart=on-failure`. It listens on `127.0.0.1:8000`. Put a reverse proxy in front.

### Fly.io

```shell
fly volumes create vatcomply_data --region ams --size 1
fly deploy --config deploy/fly.toml
```

`deploy/fly.toml` trusts `Fly-Client-IP`. The public Cloudflare setup is in `deploy/PRODUCTION.md`.

## Configuration

Every setting is an environment variable. `vatcomply --help` prints the same list.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Listen port |
| `BIND` | `0.0.0.0` | Listen address |
| `DATA_DIR` | `./data` (Docker `/data`) | Atomic rate snapshot directory |
| `RATES_REFRESH_SECS` | `3600` | ECB refresh interval |
| `VIES_TIMEOUT_SECS` | `10` | Per-attempt VIES timeout |
| `VIES_CACHE_TTL_SECS` | `300` | Cache TTL for `valid: true` results |
| `RATE_LIMIT_RPS` | `0` | Requests per second per client IP. `0` is off. Public deploy files set `2` |
| `RATE_LIMIT_BURST` | `4` | Burst size |
| `TRUSTED_IP_HEADER` | empty | Client IP header. Empty uses the socket peer. `X-Forwarded-For` is never read unless this names it |
| `GEO_COUNTRY_HEADERS` | `CF-IPCountry,Cdn-RequestCountryCode` | First matching header wins |
| `GEOIP_DB_PATH` | empty | Optional MaxMind country `.mmdb`, used only when no country header matches |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Absolute origin written into `GET /` |
| `LOG_FORMAT` | `pretty` | `pretty` or `json` |
| `LOG_LEVEL` | `info` | `tracing` filter |
| `METRICS` | `0` | `1` mounts `GET /metrics` |

`ECB_HIST_URL`, `ECB_HIST_90D_URL`, and `VIES_URL` override the upstream URLs. Leave them unset in production.

`/health`, `/healthz`, `/ready`, `/readyz`, and `/metrics` are not rate limited.

## Reverse proxy and Cloudflare

Terminate TLS at the proxy. Forward only the headers you name.

For Cloudflare:

```shell
TRUSTED_IP_HEADER=CF-Connecting-IP
```

Leave `GEO_COUNTRY_HEADERS` at the default so `CF-IPCountry` fills `/geolocate`. Cache `/rates`, `/vat_rates`, `/countries`, `/currencies`, and the OpenAPI documents at the edge. Bypass `/vat` and `/geolocate`. Details are in [`deploy/PRODUCTION.md`](deploy/PRODUCTION.md).

## Operate

- `GET /healthz` — process is up.
- `GET /readyz` — JSON with the loaded rates date, age, source (`embedded`, `disk`, or `ecb`), and any non-closed VIES breakers. `503` until a book is loaded.
- `GET /ready` — the v1 database shim, while a book is loaded.
- `GET /docs` — Scalar. The script is served from `/docs/scalar.js` on the same origin.
- `GET /openapi.json` and `GET /docs/openapi.json` — the same document. The second uses `application/vnd.oai.openapi+json`.

Stop with SIGTERM or SIGINT. The process stops accepting, drains in-flight requests, cancels the refresh task, and writes the snapshot.

## Development

Rust 1.91.1 (`rust-toolchain.toml`).

```shell
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test
```

Tests use wiremock. They do not call ECB or VIES. Golden fixtures live in `tests/golden/`. Regenerate the OpenAPI snapshot with:

```shell
UPDATE_OPENAPI=1 cargo test --test openapi
```

`bench/oha.sh` load-tests `/rates`, `/countries`, `/vat_rates`, and `/currencies`. It is not a CI gate.

Fuzz targets (`ecb_xml`, `vies_soap`, `query`) live in `fuzz/` and run on the weekly workflow, not on pull requests.

Intentional differences from v1 are in [`PLAN.md`](PLAN.md) section 7.
