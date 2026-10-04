# VATComply v2 — Rust rewrite plan

Status: approved. The crate lives at the repository root on `feat/v2-rust`. Python is deleted on that branch and remains only in git history.

The decisions in the table below were accepted with the plan. Decision 1 first placed the crate in `v2/` beside Python. The hard cut moved it to the repository root and removed the Python service.

Evidence for the contracts below is the code in `vatcomply/api.py` plus live responses from `https://api.vatcomply.com` captured on 2026-10-04 (User-Agent required; Cloudflare returns 1010 otherwise). Samples that matter are quoted. A polite recorder in M0 freezes the rest as golden files.

## Decisions that need a yes

These are the choices that change the build. Approving the plan approves the recommended answer. Object in review if you want the other one.

| # | Question | Recommendation |
|---|---|---|
| 1 | Where does the Rust tree live? | `v2/` inside this repo. Python CI stays untouched. A new repo splits the golden source away from the code it must match. |
| 2 | Image name | `ghcr.io/madisvain/vatcomply` |
| 3 | Extra env vars beyond the locked list | Add `PUBLIC_BASE_URL`, `RATE_LIMIT_RPS`, `RATE_LIMIT_BURST`, `GEO_COUNTRY_HEADERS`, `METRICS`. Details in section 4. |
| 4 | Legacy `/ready` body mentions a database | Keep the current JSON as a shim while rates are loaded. Real status goes on `/readyz`. |
| 5 | Open circuit breaker | `503` with `{"detail":"MS_UNAVAILABLE"}` and `Retry-After: 5`. |
| 6 | VIES cache | Default TTL 300s. Cache only `valid: true`. Do not cache faults or `valid: false`. |
| 7 | 90-day refresh vs v1 `ignore_conflicts` | Overwrite dates present in the feed so an ECB correction lands. |
| 8 | `f64` | Store ECB strings. One module, `rates/pyfloat.rs`, may use `f64` only to copy CPython's JSON float tokens and the 6-decimal cross-rate. It is oracle-tested. This is the only way to match production bytes. |
| 9 | Rate limit default | Binary default off (`RATE_LIMIT_RPS=0`), so `docker run` is quiet. Production compose and Fly set `RATE_LIMIT_RPS=2` and `RATE_LIMIT_BURST=4`. |
| 10 | `/docs` UI | Scalar, assets embedded, same path. No jsDelivr call. |

If M0 finds any historical date whose ECB-derived JSON differs from production, stop and ask for a dump of the `vatcomply_rate` table. Do not paper over the diff.

---

## 1. Endpoint inventory

Common rules, observed on every JSON route:

- Compact JSON, UTF-8, no trailing newline, no ASCII escaping of non-ASCII (`🇪🇪` stays UTF-8). `Content-Type: application/json` with no charset.
- Object key order is the order below. It is observable and golden tests compare bytes.
- Unknown query parameters are ignored (`/rates?foo=1` is a normal rates call).
- A trailing slash is the same route and returns 200 with the same body (`/rates/`, `/countries/`, `/vat_rates/`).
- `POST` to a known path is **404** `{"detail":"Not Found"}`, not 405.
- `HEAD` to a known path is **404** with an empty body. Axum's automatic HEAD-follows-GET must be turned off.
- `OPTIONS` is **204**, empty body, `Content-Type: application/json`, `Allow: GET, OPTIONS`, and the CORS headers below.
- Error JSON uses `detail`, not `error`. The markdown docs are stale. The `{field: [messages]}` middleware never fires for these GET routes.
- Missing required query parameter is **422** `{"detail":"Missing required query parameter: <name>"}`.
- There is no `Cache-Control` or `ETag` today. Adding them is an intentional additive change (section 7).
- CORS: when `Origin` is present, `Access-Control-Allow-Origin: *`. Preflight also sends `Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS` and `Access-Control-Allow-Headers: Content-Type, Authorization`.
- Rate limit, when enabled as in production: **429**, header `retry-after: 1`, header `x-ratelimit-limit: 2` (seen on 429, not on 200), body exactly `{"detail":"Rate limit exceeded. Try again in 1 seconds.","retry_after":1}`. The plural "seconds" is part of the contract. Code is `rps=2`, `burst=4`, keyed by client IP. `/health` and `/ready` are registered outside the throttle decorator.

### `GET /`

200. Field order:

```json
{"name":"VATComply API","version":"1.0.0","status":"operational","description":"VAT validation API, geolocation tools, and ECB exchange rates","documentation":"https://api.vatcomply.com/docs","openapi":"https://api.vatcomply.com/docs/openapi.json","endpoints":{"countries":".../countries","currencies":".../currencies","geolocate":".../geolocate","iban":".../iban","vat":".../vat","vat_rates":".../vat_rates","rates":".../rates"},"contact":"support@vatcomply.com"}
```

Absolute URLs come from `BASE_URL` (production: `https://api.vatcomply.com`). `endpoints` includes `vat_rates`. The docs example omits it and points `documentation` at www. Production does not.

Self-host: `PUBLIC_BASE_URL` (default `http://localhost:8000`). No trailing slash. Paths are joined the way production joins them.

### `GET /rates`

Query: `base` (default `EUR`), `symbols` (optional), `date` (optional, `YYYY-MM-DD`).

200 body, field order `date`, `base`, `rates`:

```json
{"date":"2026-10-02","base":"EUR","rates":{"EUR":1.0,"USD":1.1225,"JPY":176.99}}
```

Behaviour, in order:

1. `base` is case-sensitive against the 33-code allow-list. `usd` and `""` are **400** `{"detail":"Base currency '<base>' is not supported."}`. Missing `base` defaults to `EUR`. Empty `base=` is present and fails.
2. `symbols` splits on `,` with **no trimming**. `USD, JPY` is **400** `{"detail":"Currency ' JPY' is not supported."}`. `USD,,GBP` is **400** `{"detail":"Currency '' is not supported."}`. Each token must be in the allow-list. Missing `symbols` and empty `symbols=` both mean "all currencies".
3. `date` must match `^\d{4}-\d{2}-\d{2}$` or **400** `{"detail":"Invalid date format: '<date>'. Expected format: YYYY-MM-DD"}`. A matching string that is not a real day (`2024-02-30`) is **400** `{"detail":"Invalid date: '<date>'. Expected a valid date in YYYY-MM-DD format."}`. Missing `date` and empty `date=` both mean today in UTC.
4. Choose the latest stored date that is `<=` the query date. The response `date` is that row's date, not the query date.
5. No such row: **404** `{"detail":"No rate data available for the specified date."}`. Confirmed for `1998-12-31`. First ECB row is `1999-01-04`.
6. Weekends, holidays, and future dates use that same "nearest earlier row" rule. Confirmed: `2018-10-13` → `2018-10-12`; `2018-01-01` → `2017-12-29`; `2099-01-04` → `2026-10-02`.
7. Inject `EUR = 1` before the row's currencies. Drop XML currencies that are not in the allow-list. Key order is `EUR`, then ECB XML order. Confirmed on the latest day: `EUR, USD, JPY, CZK, DKK, GBP, HUF, PLN, RON, SEK, CHF, ISK, NOK, TRY, AUD, BRL, CAD, CNY, HKD, IDR, ILS, INR, KRW, MXN, MYR, NZD, PHP, SGD, THB, ZAR`. `BGN`, `HRK`, and `RUB` are absent from that day and present on older days.
8. `symbols` filters **after** that ordering. It does not reorder to the query. `symbols=USD,GBP,EUR` on `2018-10-13` returned `EUR, USD, GBP`. The base currency is omitted from `rates` when `symbols` does not name it, and `base` still reports it. Confirmed: `base=USD&symbols=GBP&date=2018-10-12` → `{"date":"2018-10-12","base":"USD","rates":{"GBP":0.757214}}`.
9. If `base` is in the allow-list but missing from **that row** (after the EUR inject): **400** `{"detail":"Base currency '<base>' not available in current rates data"}` with no trailing period. Confirmed: `base=RUB&date=2022-03-02`, `base=HRK&date=2023-01-03`, `base=BGN` on the latest day. Do not walk backward to an older row that still contains the currency. The row is chosen first; membership is checked second. `2022-03-01` still has `RUB` in the ECB file; `2022-03-02` is a published day without it.

Number formatting, confirmed against the ECB file (`eurofxref-hist.xml`, 8 191 474 bytes) and production:

- ECB publishes decimal strings. `BGN` is the string `1.9558` (not the legal 5-decimal peg). Latest-day strings match production (`USD` `1.1225`, `GBP` `0.85033`, `IDR` `20149.32`, …).
- Integral ECB strings are emitted as JSON floats with a trailing `.0`. ECB `ISK` `137` is production `137.0`. `EUR` is `1.0`, not `1`.
- Cross-rate (`base` other than `EUR`) matches this Python, which is what `vatcomply/api.py` runs:

```python
base_rate = Decimal(str(float(base_string)))
value = float(round(Decimal(str(float(rate_string))) / base_rate, 6))  # HALF_EVEN
# EUR: float(round(Decimal("1") / base_rate, 6))
# then CPython json.dumps of that float
```

Checked: `2018-10-12` USD base → `EUR` `0.864006`, `GBP` `0.757214`. `2022-12-30` HRK base → `EUR` `0.132688`, `USD` `0.141525`. `2025-12-31` BGN base → `EUR` `0.5113`, `USD` `0.600777` (the 6-decimal quantize of `1/1.9558` is `0.511300`, and JSON drops the trailing zeros).

Allow-list, in response order for `/currencies` and for validation: `EUR USD JPY BGN CZK DKK GBP HUF PLN RON SEK CHF ISK NOK HRK RUB TRY AUD BRL CAD CNY HKD IDR ILS INR KRW MXN MYR NZD PHP SGD THB ZAR` (33).

### `GET /countries`

200, JSON array, sorted by `iso2` ascending. Production count **250**, first `AD`, last `ZW`. `GR` is present, `EL` is not.

Each object, this key order: `iso2`, `iso3`, `name`, `numeric_code` (int), `phone_code` (string, no `+`), `capital`, `currency`, `tld`, `region`, `subregion`, `latitude`, `longitude`, `emoji`.

Empty capital (string `""`, not null): `AQ`, `BV`, `HM`, `TK`, `UM`. Empty subregion: `AQ`, `BV`, `HM`. Whole-number coordinates are `59.0`, not `59`.

Filters are AND. `search` is case-insensitive substring of `name`, `iso2`, or `iso3` (`EE` can match more than Estonia). `region`, `subregion`, and `currency` are case-insensitive **equality**. Unknown filters return `[]`.

### `GET /currencies`

200, JSON object, 33 keys, allow-list order above. `search` is a case-insensitive substring of the code **or** the English name. `search=us` therefore matches any name containing "us" (including "Russian"). `search=zzzzzzz` is `{}`. Empty search returns all.

Value key order: `name`, `symbol`, `numeric_code` (string, `"840"`), `currency_symbol`, `currency_symbol_narrow` (always `null` today), `decimal_places`, `rounding`, `countries` (sorted territory codes, including non-ISO such as `DG`, `EA`, `QZ` if present in the snapshot).

Confirmed: USD name `US Dollar`, symbol `$`, numeric `840`, 2 decimals, rounding 0. JPY and ISK have `decimal_places` 0. HUF has 2. EUR symbol is `€`.

Do not recompute this from CLDR. Embed the production object. Babel/CLDR drift would change names and territory lists.

### `GET /vat_rates`

200, array ordered by `country_code`. Unknown code, including `GR`, is `[]`. `country_code` match is case-insensitive (`de` → `DE`).

27 rows: `AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK`. Greece is `EL`, `country_name` `Greece`. There is no `XI` row.

Key order: `country_code`, `country_name`, `standard_rate`, `reduced_rates`, `super_reduced_rate`, `parking_rate`, `currency`, `member_state`, `rate_comments`, `rate_categories`.

`member_state` is `true`. `super_reduced_rate` and `parking_rate` are JSON `null` when absent. Rates are JSON numbers (`19.0`, `25.5`, `2.1`). `rate_comments` maps a **string** rate key (`"7.0"`, `"19.0"`, `"0.0"`) to a list of strings. `rate_categories` maps a lowercased TEDB identifier to a list of numbers. Both are `{}` when empty. Germany's comment payload is large (about 8 KB for `DE` alone, about 237 KB for the full list). Embed it whole.

Production standard rates on 2026-10-04 (the in-repo tests are stale: they still expect Estonia 22): AT 20, BE 21, BG 20 EUR, CY 19, CZ 21 CZK, DE 19, DK 25, EE 24, EL 24, ES 21, FI 25.5, FR 20, HR 25, HU 27 HUF, IE 23, IT 22, LT 21, LU 17, LV 21, MT 18, NL 21, PL 23 PLN, PT 23, RO 21 RON, SE 25, SI 22, SK 23.

### `GET /vat`

Query `vat_number` required.

Local checks, before any network:

- Pattern `^[A-Z]{2}[0-9A-Z]{8,12}$`. Failure, including empty, lowercase (`gb…`), spaces, punctuation, and the wrong length: **400** `{"detail":"Invalid VAT number format. Expected format: Two-letter country code followed by 8-12 digits or letters."}`.
- Prefix `GB` after the pattern passes: **400** with this exact string: `As of 01/01/2021, the VoW service to validate UK (GB) VAT numbers ceased to exist while a new service to validate VAT numbers of businesses operating under the Protocol on Ireland and Northern Ireland appeared. These VAT numbers are starting with the "XI" prefix.`
- No normalisation. A short Romanian number that VIES would accept fails the pattern. Keep that.
- `XI` is allowed when the pattern matches. `EL` is the Greek prefix. `GR…` passes the pattern and is sent to VIES.

VIES `checkVat` then:

- 200, key order `valid`, `vat_number`, `country_code`, `name`, `address`. `vat_number` and `country_code` are the VIES values (national number, no prefix). `address` is end-stripped only; internal double spaces stay. Unicode is preserved. `name` is JSON `null` when VIES sends nil, and a string otherwise (often `"---"`). `valid: false` from VIES is still **200**.
- SOAP fault whose stripped faultstring is **exactly** one of `MS_MAX_CONCURRENT_REQ`, `MS_MAX_CONCURRENT_REQ_TIME`, `MS_UNAVAILABLE`, `SERVICE_UNAVAILABLE`, `TIMEOUT`, `GLOBAL_MAX_CONCURRENT_REQ`: retry up to 3 attempts, backoff 0.4s then 0.8s, concurrency cap 4. After exhaustion: **503** `{"detail":"<faultstring>"}` and header `Retry-After: 5`. Body has no `retry_after` field.
- Any other fault, including `INVALID_INPUT`: **400** `{"detail":"<faultstring>"}`, no retry. Confirmed live: `XX12345678` → `{"detail":"INVALID_INPUT"}`.
- Timeout per attempt is 10s today (`VIES_TIMEOUT_SECS` default 10).
- Do not log the full VAT number at info. Log the country prefix and the fault code.

### `GET /iban`

Query `iban` required. 200 key order: `valid`, `iban`, `bank_name`, `bic`, `country_code`, `country_name`, `checksum_digits`, `bank_code`, `branch_code`, `account_number`, `bban`, `in_sepa_zone`.

`valid` is `true` on every 200. The `iban` field is the raw query value, not a canonical form. Confirmed: `DE89370400440532013000` → bank `Commerzbank`, BIC `COBADEFFXXX`, country `DE` / `Germany`, checksum `89`, bank code `37040044`, branch `""`, account `0532013000`, bban `370400440532013000`, `in_sepa_zone` true.

400s come from schwifty's messages, passed through as `detail`. Confirmed: empty → `Invalid characters in IBAN ` (trailing space); `123` → `Invalid characters in IBAN 123`; bad checksum `DE89370400440532013001` → `Invalid checksum digits`. M0 records a wider matrix (unknown country, wrong length, lowercase, spaces). The markdown example for `GB82WEST…` is not evidence; capture the live body.

### `GET /geolocate`

No query parameters. Country from `CF-IPCountry`, else `Cdn-RequestCountryCode`. `ip` from `CF-Connecting-IP`, or JSON `null` when that header is absent.

200 key order: `iso2`, `iso3`, `country_code`, `name`, `numeric_code`, `phone_code`, `capital`, `currency`, `tld`, `region`, `subregion`, `latitude`, `longitude`, `emoji`, `ip`. `country_code` is the header value uppercased. The rest is the countries row.

404s, exact:

- No header: `{"detail":"Country code not received from CDN headers (CF-IPCountry or Cdn-RequestCountryCode)."}`
- Unknown code: `{"detail":"Data for country code `XX` not found."}` (backticks around the uppercased code). Cloudflare specials such as `T1` hit this path when they are not in the country table.

Production sits behind Cloudflare, so a normal request is geolocated without the caller setting a header. The golden geolocate success fixture must inject the headers in-process. Do not record the edge's view of the recorder's IP as the success fixture.

### Health and docs, as they are today

| Path | Status | Body |
|---|---|---|
| `GET /health` | 200 | `{"status":"ok"}` |
| `GET /ready` | 200 | `{"status":"healthy","checks":{"check_database":{"healthy":true,"message":"Database connection OK"}}}` |
| `GET /healthz`, `GET /readyz` | 404 | `{"detail":"Not Found"}` |
| `GET /docs` | 200 | Swagger UI HTML, `text/html`, loads jsDelivr |
| `GET /docs/openapi.json` | 200 | OpenAPI 3.1, `Content-Type: application/vnd.oai.openapi+json`, title `Vatcomply API` 1.0.0. Paths: `/`, `/countries`, `/currencies`, `/geolocate`, `/health`, `/iban`, `/rates`, `/ready`, `/vat`, `/vat_rates` |

`/openapi.json` and `/metrics` do not exist today.

### VIES REST, evaluated

The Commission publishes a REST API next to SOAP. Spec: `https://ec.europa.eu/assets/taxud/vow-information/swagger_publicVAT.yaml` (Swagger 2.0).

- `POST https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number`
- `POST https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-test-service`
- `GET  https://ec.europa.eu/taxation_customs/vies/rest-api/check-status`

A live call to the **test** service with `{"countryCode":"DE","vatNumber":"100"}` returned 200, `valid: true`, name `John Doe`. The REST schema returns `userError` / `errorWrappers` in the JSON body, and callers have been bitten by `valid: false` combined with `MS_MAX_CONCURRENT_REQ` (HTTP 200, no SOAP fault). v1's mapping is exact faultstring equality on SOAP faults, and that is what the tests lock.

v2 ships the SOAP client, behind a small `ViesClient` trait. REST is not the v2 transport. The test service is useful for an optional manual check and is not part of CI.

---

## 2. Findings

The handover matches the service in outline and differs from it in these facts:

- The live app is Django Bolt (`vatcomply/api.py`), not the Django Ninja layout described in `Claude.md`. Routes are `/`, `/rates`, `/vat`, `/vat_rates`, `/geolocate`, `/countries`, `/currencies`, `/iban`, `/health`, `/ready`, `/docs`, `/docs/openapi.json`.
- Docs say errors look like `{"error": "..."}`. Production and the tests say `{"detail": "..."}`. Follow production.
- Docs show a 422 body of `{field: [messages]}`. Production 422 for a missing query parameter is `{"detail":"Missing required query parameter: vat_number"}`.
- v1 stores rates as Python floats (`float()` on the XML attribute, SQLite JSON, `ignore_conflicts=True`). The latest ECB file still matches production after CPython's float JSON encoding, including `137` → `137.0`. Cross-rates are a 6-decimal HALF_EVEN division of those float-strings. "Never `f64`" and "byte-for-byte with production" meet in `rates/pyfloat.rs` (decision 8). Storage itself stays a decimal string.
- v1's scheduler is cron: rates at minute 10 (90-day file, insert-only), countries 02:00, VAT rates 03:00. The handover's hourly `tokio::time::interval` with `MissedTickBehavior::Skip` replaces that. First tick at startup. Full `eurofxref-hist.xml` when no valid disk snapshot exists; `eurofxref-hist-90d.xml` otherwise.
- Countries source is `dr5hn/countries-states-cities-database` `countries.json` (`phonecode` → `phone_code`). VAT rates source is TEDB SOAP `retrieveVatRates` (`VatRetrievalService.wsdl`), Greece mapped `EL`. v2 does not call those on the request path. It embeds a snapshot taken from production.
- Geolocation is two headers, not one: `CF-IPCountry` then Bunny `Cdn-RequestCountryCode`. There is no MaxMind database today.
- Client IP for the `ip` field is specifically `CF-Connecting-IP`. Rate limiting in production is 2 rps, burst 4. The handover knob was per minute. v2 keeps only `RATE_LIMIT_RPS` and `RATE_LIMIT_BURST`, so the header `x-ratelimit-limit: 2` stays true in production.
- `/health` and `/ready` exist and monitors use them. `/healthz` and `/readyz` are new names from the handover. Keep the old ones.
- Root and OpenAPI URLs are on `api.vatcomply.com`, including `documentation` → `https://api.vatcomply.com/docs`.
- Local `db.sqlite3` has 62 rate rows (2025-10-20 through 2026-01-16), 0 countries, and 27 VAT-rate rows. It is not the golden source. Production HTTP is.
- No response caching headers today (`cf-cache-status: DYNAMIC`). Section 8 of the handover wants the edge to honour origin `Cache-Control`. v2 adds the headers; the edge rules in `deploy/PRODUCTION.md` do the rest.

---

## 3. Layout and types

```
PLAN.md                          # this document, repo root, after approval
v2/
  Cargo.toml
  rust-toolchain.toml            # stable, pinned
  Dockerfile
  dist-workspace.toml            # cargo-dist
  README.md                      # self-hosting; root README later links here
  src/
    main.rs                      # mimalloc, argv: serve (default) | healthcheck, shutdown
    config.rs
    error.rs                     # detail JSON, status, Retry-After
    state.rs
    http/
      mod.rs                     # router, layers, HEAD→404, trailing slash
      cors.rs
      limit.rs
      cache.rs                   # Cache-Control, ETag
      ip.rs                      # TRUSTED_IP_HEADER only
    rates/
      mod.rs
      parse.rs                   # ECB XML → decimal strings, quick-xml
      pyfloat.rs                 # CPython-compatible token + cross-rate
      book.rs                    # sorted rows, lookup, precomputed latest Bytes
      snapshot.rs                # versioned, checksum, atomic rename, gzip
      refresh.rs                 # interval, retry, CancellationToken
    vies/
      mod.rs                     # trait + retry + semaphore
      soap.rs
      breaker.rs                 # per-country
      cache.rs                   # moka, valid=true only
    data/
      countries.rs
      currencies.rs
      vat_rates.rs
    geo.rs
    openapi.rs
  data/
    countries.json               # production snapshot
    currencies.json
    vat_rates.json
    rates-snapshot.json.gz       # embedded fallback, include_bytes!
    iban_registry.json           # vendored structures + bank names
  tests/
    golden.rs
    golden/*.json                # {request, status, headers, body}
    openapi_snapshot.rs
    rates.rs
    vies.rs
    resilience.rs
  tests/fixtures/
    ecb/*.xml
    vies/*.xml                   # success + every fault
    pyfloat_oracle.json
  fuzz/                          # cargo-fuzz: ecb, soap, query
  bench/oha.sh
  deploy/
    docker-compose.yml
    vatcomply.service
    fly.toml
    PRODUCTION.md
  tools/
    record_golden.py             # polite production recorder
    refresh_snapshot.py          # ECB → rates-snapshot.json.gz
.github/workflows/v2.yml
```

One package, one binary, `vatcomply`. No workspace. Python stays at the repo root.

Key types:

- `Config` — env only, documented by `--help`. Missing a documented default is a bug.
- `ApiError` — `{ status, detail, headers }`. Encoded as `{"detail":...}` with `Cache-Control: no-store`. No `unwrap` on this path.
- `RateBook` — `Vec<RateRow>` sorted by date. `RateRow` holds the date plus `(code, decimal string)` in XML order, EUR not stored. Lookup is binary search for the rightmost date `<=` query.
- `RatesState` — `RateBook`, `fetched_at`, `source` (`embedded` | `disk` | `ecb`), and `latest: Bytes` for the default `/rates` body. Published through `ArcSwap`.
- `ViesClient` — `async fn check(country, number) -> Result<VatHit, ViesFault>`. SOAP is the only impl. `ViesFault` is `Transient(String)` or `Permanent(String)` based on exact faultstring equality.
- `Breaker` — per country code, consecutive-transient count, open-until instant. Open → `MS_UNAVAILABLE` without a call.
- Static data is parsed and checked at startup (counts, required EU members, allow-list, Greece `EL` in VAT rates and `GR` in countries). Failure to parse aborts the process.

Startup:

1. Parse embedded snapshot. Abort if it is corrupt (it is compile-time data).
2. If `$DATA_DIR/rates-snapshot.json.gz` verifies, and its max date is newer or equal, use it.
3. Mark ready and bind. Embedded data is enough.
4. Spawn the scheduler. First tick immediately. No valid disk file → full history. Otherwise the 90-day feed. Three tries, backoff, per-attempt timeout, cancel on shutdown.
5. On success, swap the book, rebuild `latest` bytes, write the snapshot (temp file, fsync, rename). On failure, keep serving and log.

A snapshot write that fails because the volume is not writable is logged and ignored. The process still serves. `FROM scratch` as UID 65532 cannot chown a fresh named volume; the one-liner without a volume must work.

Shutdown on SIGINT/SIGTERM: stop accept, drain with a timeout, cancel the scheduler, best-effort flush.

`vatcomply healthcheck` GETs `http://127.0.0.1:$PORT/healthz` and exits 0 on 200. The Docker `HEALTHCHECK` is that command.

Request path for `/rates`: read `ArcSwap`, copy the `Bytes` when the query is the default, otherwise build the body from decimal strings through `pyfloat`. Historical responses are not precomputed; thirty currencies is nothing next to VIES.

---

## 4. Dependencies

Runtime, each earned:

| Crate | Why |
|---|---|
| `tokio` | Runtime, interval, signals. Locked. |
| `axum` | HTTP. Locked. |
| `tower` | Layer stack. Locked. |
| `tower-http` | Compression, timeout, trace, `CatchPanicLayer`, CORS. Locked. |
| `tower_governor` | IP rate limit. Locked. Custom body so the 429 JSON matches v1. |
| `reqwest` | ECB and VIES. `default-features = false`, `rustls-tls-webpki-roots`. No OpenSSL. |
| `quick-xml` | ECB and SOAP. Locked. |
| `arc-swap` | Published rate book. Locked. |
| `moka` | VIES success cache. Locked. |
| `mimalloc` | Global allocator. Locked. If musl link fails, stop and ask before swapping it out. |
| `indexmap` | Keep currency key order while parsing the embedded JSON object. |
| `serde` + `serde_json` | Config and JSON bodies. `raw_value` keeps the embedded slices. |
| `bytes` | Precomputed latest-rates body. |
| `rust_decimal` | Scale-6 HALF_EVEN division in the cross-rate. |
| `sha2` | Snapshot checksum. |
| `flate2` | Gzip the embedded snapshot. |
| `tracing` + `tracing-subscriber` | JSON or pretty logs, one line per request. |
| `tokio-util` | `CancellationToken` for the scheduler. |
| `utoipa` + `utoipa-axum` | Spec and routes registered together. Locked. |
| `utoipa-scalar` | `/docs`, assets embedded. If a version pulls a CDN, vendor the file instead. |
| `maxminddb` | GeoIP only when `GEOIP_DB_PATH` is set. Locked. |
| `prometheus` | `/metrics` text when `METRICS=1`. |

Dev: `wiremock`, `proptest`. Fuzzing uses `cargo-fuzz` and `libfuzzer-sys` in `fuzz/`, not in the server's dependency tree. The committed `openapi.json` is the oasdiff baseline.

Not used, on purpose: `clap` (hand-rolled `--help` and the `healthcheck` argv), `thiserror`, `anyhow`, `chrono`, `regex`, `openssl`.

Env:

| Var | Default | Notes |
|---|---|---|
| `PORT` | `8000` | |
| `BIND` | `0.0.0.0` | |
| `DATA_DIR` | `./data` | Docker `/data` |
| `RATES_REFRESH_SECS` | `3600` | |
| `VIES_TIMEOUT_SECS` | `10` | Per attempt |
| `VIES_CACHE_TTL_SECS` | `300` | |
| `RATE_LIMIT_RPS` | `0` | 0 = off. Production sets `2`. |
| `RATE_LIMIT_BURST` | `4` | Used with RPS. |
| `TRUSTED_IP_HEADER` | empty | Empty = socket peer only. Production: `CF-Connecting-IP`. Never `X-Forwarded-For` unless this var names it. |
| `GEO_COUNTRY_HEADERS` | `CF-IPCountry,Cdn-RequestCountryCode` | First hit wins. |
| `GEOIP_DB_PATH` | empty | Used only when no country header matched. |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Root links. Production: `https://api.vatcomply.com`. |
| `LOG_FORMAT` | `pretty` | `json` or `pretty` |
| `LOG_LEVEL` | `info` | |
| `METRICS` | `0` | `1` mounts `/metrics`. |

Optional test overrides, documented as advanced, defaulting to the official URLs: `ECB_HIST_URL`, `ECB_HIST_90D_URL`, `VIES_URL`. Tests point these at wiremock. They are not required to self-host.

Health and readiness are not rate-limited. `/metrics` is not either.

Cache-Control:

- Default `/rates` (no date): `public, max-age=300`, strong ETag of the body.
- `/rates` with a date, `/countries`, `/currencies`, `/vat_rates`, both OpenAPI paths: `public, max-age=86400`, strong ETag.
- `/vat`, `/geolocate`: `private, no-store`.
- Errors, including 429 and 503: `no-store`.
- `/` : `public, max-age=60`.

`Access-Control-Allow-Origin: *` on every response, so a cached body is safe to share. Production only adds the header when `Origin` is set. That is an intentional additive difference.

---

## 5. Milestones

Each milestone ends with `cargo fmt`, `cargo clippy --all-targets -- -D warnings`, and `cargo test` green, plus a short note of what changed, what is left, and any new question. No network in tests.

### M0 — skeleton, CI, fixtures

Scope: `v2/` package, pinned toolchain, `.github/workflows/v2.yml` (fmt, clippy, test, `cargo deny`). Config, `--help`, `healthcheck`, `/health`, `/healthz`, `/ready` shim, `/readyz` (rates age, source, breaker map; age is null before M2 and `/readyz` returns 503 until a book is loaded). Tracing. Graceful shutdown. Golden recorder and the first fixtures.

Acceptance:

- `PLAN.md` is at the repo root.
- CI is green on a PR that only touches `v2/` and the workflow.
- `tests/golden/` contains, with the request that produced them: every error body quoted in section 1; one success body each for `/`, `/countries?search=Estonia`, `/currencies?search=USD`, `/vat_rates?country_code=DE`, `/vat_rates?country_code=EL`, `/iban` for the Deutsche Bank sample and the checksum failure; `/rates` for `1999-01-04`, `2017-12-29`, `2018-10-12`, `2018-10-13`, `2022-02-28`, `2022-03-01`, `2022-03-02`, `2022-12-30`, `2023-01-03`, `2025-12-31`, the latest day captured that morning, and the cross-rate samples in section 1. Full `/countries`, `/currencies`, and `/vat_rates` bodies are stored as `data/*.json` and as golden files.
- Recorder sleeps so it stays under 2 rps, and sends a browser User-Agent.
- A Python script writes `pyfloat_oracle.json` for every distinct ECB rate string in the downloaded history, plus the cross-rate samples. Committed. No Python at test runtime.
- Recorded ECB XML excerpts (first day, a gap, a RUB day, a HRK day, a post-BGN day, the 90-day file) and VIES SOAP fixtures for success, `valid=false`, and each fault in section 1. Fault fixtures may be constructed from the WSDL if a live fault is not captured; label them `synthetic` in the filename when so.

### M1 — static endpoints and OpenAPI

Scope: `/countries`, `/currencies`, `/vat_rates`, `/`, `/docs`, `/docs/openapi.json`, `/openapi.json`. Filters. Startup validation that all 27 VAT-rate member states are present and that `GR` exists in countries.

Acceptance:

- Golden files for those routes match bytes, including key order, `59.0`, `19.0`, `currency_symbol_narrow: null`, and `EL`.
- `insta` snapshot of the utoipa spec. `Content-Type` of `/docs/openapi.json` is `application/vnd.oai.openapi+json`.
- `/docs` returns HTML with no external URL in it.
- Unknown country filter and `country_code=zz` match golden.

### M2 — rates

Scope: parser, book, `pyfloat`, snapshot, embedded fallback, scheduler, `/rates`.

Acceptance:

- Every rates golden file matches bytes, including `137.0`, `0.5113`, `0.864006`, the empty-symbol and empty-date quirks, and the "not available" errors.
- `pyfloat` matches the oracle for every entry.
- Test: ECB down at startup serves the embedded book and `/readyz` says `embedded`.
- Test: corrupt disk snapshot is logged and ignored, embedded is served.
- Test: 90-day refresh inserts a missing day and overwrites a day whose string changed.
- Test: weekend and a date before `1999-01-04`.
- No `f64` outside `pyfloat.rs` and tests. Grep is part of the milestone note.

### M3 — VIES

Scope: SOAP client, retries, semaphore of 4, per-country breaker, moka cache, `/vat`.

Acceptance:

- Golden: format error, Brexit text, `XX12345678` → `INVALID_INPUT`, a `valid: true` fixture, a `valid: false` fixture.
- Wiremock: each transient fault retries twice then 503 with `Retry-After: 5`; a transient then success returns 200; `INVALID_INPUT` tries once.
- Breaker: five consecutive transient faults open that country; the next call does not hit the mock and returns `MS_UNAVAILABLE`; after cool-down a success closes it. Another country is unaffected.
- Cache: second `valid: true` does not hit the mock; `valid: false` does, twice.
- Log line for a VAT call does not contain the full number.

### M4 — geo, limits, cache, CORS, IBAN

Scope: the remaining edges.

Acceptance:

- Geolocate golden, both headers, missing header, unknown code, `ip` null when `CF-Connecting-IP` is absent.
- With `GEOIP_DB_PATH` unset, behaviour matches v1. A unit test with a tiny fixture mmdb covers the fallback when the header is missing.
- IBAN golden, including schwifty's error strings. Spike the `iban` crate against the fixtures first; if bank name, BIC, or error text differs, use `data/iban_registry.json` exported from the schwifty version already in this repo.
- 429 body and headers match section 1 when `RATE_LIMIT_RPS=2` and `RATE_LIMIT_BURST=4`. Health routes stay 200 under the same burst.
- CORS preflight matches the recorded headers. `ACAO: *` is present without an `Origin`.
- `ETag` and `Cache-Control` match section 4. `no-store` on 400 and 503.
- `HEAD /rates` is 404. `POST /rates` is 404 with the detail body. Trailing slash matches the non-slash golden body.

### M5 — packaging and README

Scope: Dockerfile (zigbuild, `x86_64-unknown-linux-musl` and `aarch64-unknown-linux-musl`, `FROM scratch`, CA certs, UID 65532, `DATA_DIR=/data`, healthcheck subcommand), `deploy/docker-compose.yml`, `deploy/vatcomply.service` (DynamicUser, StateDirectory, ProtectSystem=strict, NoNewPrivileges, restart), `deploy/fly.toml`, cargo-dist (Linux musl x86_64/aarch64, macOS x86_64/arm64, Windows, shell and PowerShell installers), README self-hosting section.

Acceptance:

- `docker run -p 8000:8000 ghcr.io/madisvain/vatcomply` serves `/healthz`, `/rates`, `/countries`, `/currencies`, `/vat_rates` with no volume and no extra env. Image under 25 MB, binary under 20 MB. If either budget is missed, report the size and stop before adding features.
- README covers: docker one-liner, compose, binary + systemd, Fly, every env var, and Cloudflare (`TRUSTED_IP_HEADER=CF-Connecting-IP`, `GEO_COUNTRY_HEADERS` left at default). A stranger can finish one of those paths in under five minutes.
- systemd unit matches the hardening flags in the handover.

### M6 — resilience, load, production doc

Scope: the remaining tests, `bench/oha.sh`, `deploy/PRODUCTION.md`, cut-over checklist.

Acceptance:

- Resilience tests from the handover: embedded fallback, corrupt snapshot, breaker open and recover, SIGTERM mid-request drains or aborts cleanly and the process exits 0.
- `oha` against a local release binary for `/rates`, `/countries`, `/vat_rates`. Record p50, p99, RPS in the milestone note. Script is committed; the numbers are not a CI gate.
- `PRODUCTION.md`: Cloudflare in front, cache rules for `/rates`, `/vat_rates`, `/countries`, `/currencies`, `/openapi.json`, `/docs/openapi.json`; bypass for `/vat` and `/geolocate`. Two EU VPS instances, each with its own volume, `cloudflared` sidecar, no public origin ports. Fly.io as the alternative (2+ EU machines, one small volume each). Uptime on `/readyz`, alert when rates age exceeds 4 days. Cut-over: v2 beside v1, shadow-compare, shift traffic at Cloudflare, v1 left running for rollback.
- `cargo deny` and `oasdiff` are in CI. `oasdiff` compares the PR spec to the spec on `main` and fails on a breaking diff unless the PR is labelled `breaking-ok`. The first PR is the baseline.
- Tag workflow `v*`: cargo-dist GitHub Release, multi-arch GHCR push, SBOM, provenance. Weekly workflow: `cargo audit`, refresh the embedded rates snapshot, open a PR when VAT rates or the snapshot changed. Fuzzing is a short weekly run, not a PR gate.

---

## 6. Risks

- **Historical drift.** Latest-day and the sampled dates match ECB plus the Python float rule. That is not a proof for every day since 1999. M0's oracle plus a few dozen live comparisons is the gate. A mismatch stops the milestone.
- **`serde_json` float tokens vs CPython.** The oracle decides. If they disagree, format inside `pyfloat.rs` and keep serde for everything that is not a rate number.
- **IBAN registry drift.** schwifty's bank names move between releases. Vendor one export and refresh it on purpose.
- **VAT rates go stale.** Estonia in the unit tests is already behind production (22 vs 24). The weekly PR job is what keeps the embedded file honest. The running process does not call TEDB.
- **mimalloc + musl.** Known to be fiddly when statically linked. Budget and the locked allocator both matter; do not swap it quietly.
- **Scratch and volumes.** A root-owned Docker volume is not writable by UID 65532. Serving still works from the embedded book. Persistence needs a pre-chowned host directory, documented in the README.
- **VIES capacity.** The breaker and the four-wide semaphore reduce `MS_MAX_CONCURRENT_REQ` storms. They also change behaviour: a country that is failing fast gets `MS_UNAVAILABLE` without a live call. Decision 5.
- **Cache at the edge.** New `Cache-Control` on `/rates` means Cloudflare will start storing it. `max-age=300` caps how stale the latest day can be. `/vat` and `/geolocate` stay `no-store`.
- **OpenAPI is a new document.** It will not match Bolt's `openapi.json` byte for byte. Paths, parameters, and status codes must still describe what section 1 describes. `oasdiff` guards later PRs, not the gap with Bolt.
- **HEAD is 404.** Some clients probe with HEAD and will see what they see today. Do not "fix" it.
- **Personal data in VAT fixtures.** A live success body contains a legal name and address. That is public VIES data and the golden file needs it. Do not log it.

---

## 7. Intentional differences

API-visible, and only these:

- New paths: `/healthz`, `/readyz`, `/openapi.json`. `/metrics` only when `METRICS=1`. Existing paths stay.
- `/ready` keeps today's JSON while a rate book is loaded. `/readyz` is the honest one (age, source, breaker states) and returns 503 when no book is loaded.
- `/docs` is Scalar with embedded assets. Path and HTTP 200 stay. `/docs/openapi.json` stays, same content type.
- `Cache-Control` and `ETag` on the cacheable GETs. `no-store` on errors.
- `Access-Control-Allow-Origin: *` even when the request has no `Origin`.
- Binary ships with rate limiting off. The public deploy files turn on 2 rps, burst 4, and then the 429 body matches v1.
- A VIES country whose breaker is open returns `MS_UNAVAILABLE` without calling the Commission. Successful validations may be up to `VIES_CACHE_TTL_SECS` old.
- Countries, currencies, and VAT rates update when a snapshot PR is merged and the binary is rebuilt, not on a daily cron inside the process.
- No database, no Django admin. `tracing` logs always. When `SENTRY_DSN` is set, panics and `ERROR` logs (including HTTP 500s) go to Sentry. VIES faults stay warnings and HTTP 503. Uptime watches `/readyz`.

Anything else that cannot match section 1 is a stop-and-ask, not a quiet difference.
