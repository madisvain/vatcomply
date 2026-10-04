# Production hosting for vatcomply.com

This document describes the reference setup. Nothing here is provisioned by the repository.

## Edge

Cloudflare sits in front of every public hostname (proxied DNS, TLS, DDoS protection, caching).

Cache rules, honouring the origin `Cache-Control`:

- Cache: `/rates`, `/vat_rates`, `/countries`, `/currencies`, `/openapi.json`, `/docs/openapi.json`
- Bypass: `/vat`, `/geolocate`

The origin sets:

- `TRUSTED_IP_HEADER=CF-Connecting-IP` for rate limiting
- `GEO_COUNTRY_HEADERS` left at the default (`CF-IPCountry,Cdn-RequestCountryCode`)

`/vat` and `/geolocate` send `Cache-Control: private, no-store`. Errors send `no-store`.

## Recommended origin

Two small EU VPS instances (for example Hetzner, different locations). Each runs the Docker image with its own `DATA_DIR` volume. Refreshes are idempotent, so the instances do not share a disk.

No public ports. A `cloudflared` sidecar on each host opens a Cloudflare Tunnel. Cloudflare balances across both tunnels and fails over when one tunnel drops.

Compose for the API itself is `deploy/docker-compose.yml`. Add the sidecar next to it:

```yaml
services:
  vatcomply:
    image: ghcr.io/madisvain/vatcomply:latest
    environment:
      DATA_DIR: /data
      PORT: "8000"
      BIND: "127.0.0.1"
      LOG_FORMAT: json
      RATE_LIMIT_RPS: "2"
      RATE_LIMIT_BURST: "4"
      TRUSTED_IP_HEADER: CF-Connecting-IP
    volumes:
      - vatcomply-data:/data
    restart: unless-stopped

  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run
    environment:
      TUNNEL_TOKEN: ${TUNNEL_TOKEN}
    restart: unless-stopped
    depends_on:
      - vatcomply

volumes:
  vatcomply-data:
```

Point the tunnel's public hostname at `http://vatcomply:8000`. Do not publish `8000` on the host.

The image runs as UID 65532. A root-owned volume logs a snapshot write error and keeps serving the embedded rate book. `chown 65532:65532` on the volume directory before the first start if the snapshot should persist.

## Alternative origin

Fly.io, two or more machines in EU regions, each with a small volume. Config: `deploy/fly.toml` (`TRUSTED_IP_HEADER=Fly-Client-IP`).

```shell
fly volumes create vatcomply_data --region ams --size 1
fly volumes create vatcomply_data --region fra --size 1
fly deploy --config deploy/fly.toml
fly scale count 2 --region ams,fra
```

If those machines also sit behind Cloudflare, set `TRUSTED_IP_HEADER=CF-Connecting-IP` instead of `Fly-Client-IP`.

## Monitoring

External uptime checks hit `/readyz`. Alert when the check fails or `rates_age_secs` is greater than 4 days (`345600`). Log shipping is optional. `/metrics` is off unless `METRICS=1`.

## Cut-over

The live process is the Railway service. It builds the root `Dockerfile` on push to `master`. GitHub Actions no longer publishes a Python image.

1. On the Railway service, while the current deployment is still serving, set `RATE_LIMIT_RPS=2`, `RATE_LIMIT_BURST=4`, `TRUSTED_IP_HEADER=CF-Connecting-IP`, `DATA_DIR=/data`, `LOG_FORMAT=json`, and mount a volume at `/data`.
2. Note the current Railway deployment id. That deployment is the rollback.
3. Merge the rewrite. Railway builds the Rust image and replaces the service. The SQLite volume is unused. Leave it until `/rates` and `/vat` have answered.
4. The volume must be writable by UID 65532. If it is not, the log shows a snapshot write error and the process still serves the embedded rates.
5. Check `https://api.vatcomply.com/rates`, `/countries`, `/vat_rates`, and one `/vat`.

If the musl link fails, the build fails and Railway keeps the previous deployment.

Confirm the API zone is not Cache Everything before the merge. `/vat` and `/geolocate` send `Cache-Control: private, no-store`. Undated `/rates` sends `max-age=300`.

Behaviour that differs from v1 on purpose is in `PLAN.md` section 7.
