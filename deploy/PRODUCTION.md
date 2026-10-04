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
cd v2
fly volumes create vatcomply_data --region ams --size 1
fly volumes create vatcomply_data --region fra --size 1
fly deploy --config ../deploy/fly.toml
fly scale count 2 --region ams,fra
```

If those machines also sit behind Cloudflare, set `TRUSTED_IP_HEADER=CF-Connecting-IP` instead of `Fly-Client-IP`.

## Monitoring

External uptime checks hit `/readyz`. Alert when the check fails or `rates_age_secs` is greater than 4 days (`345600`). Log shipping is optional. `/metrics` is off unless `METRICS=1`.

## Cut-over

1. Deploy v2 beside v1. Leave v1 serving production traffic.
2. Mirror a slice of production traffic at v2 and shadow-compare status, path, and JSON body against v1. Historical `/rates` that disagree with the ECB-derived body stop the cut-over until a `vatcomply_rate` dump explains them.
3. Shift traffic gradually at Cloudflare (tunnel weight or a staged DNS move).
4. Keep v1 running and ready for an instant rollback for the whole bake period.
5. After the bake, leave v1 in place until a rollback is no longer required. The Python service in this repository is unchanged until that point.

Known behaviour that shadow-compare will flag on purpose is listed in `PLAN.md` section 7 (new health paths, cache headers, CORS without `Origin`, breaker short-circuit, VIES cache, rate limit off unless the deploy files set it).
