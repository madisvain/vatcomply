# CLAUDE.md

VATComply is a Rust HTTP service: EU VAT validation (VIES), VAT rates, ECB exchange rates, IBAN checks, and IP/country geolocation.

The crate is at the repository root. `docs/` is the public website and is published by `.github/workflows/docs.yml`. Python sources for the previous API exist only in git history.

## Commands

```shell
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test
cargo deny check
```

Rust 1.91.1 is pinned in `rust-toolchain.toml`. Tests use wiremock and do not call ECB or VIES.

```shell
cargo build --release
```

The release profile is `lto = "fat"`, `codegen-units = 1`, `opt-level = 3`, `strip = true`. The binary listens on `PORT` (default 8000). `vatcomply --help` lists the environment variables. `vatcomply healthcheck` is the Docker health check.

## Layout

- `src/` — axum service. Rates stay decimal strings. `src/rates/pyfloat.rs` is the only module that formats ECB cross-rates the way the previous API did.
- `data/` — embedded countries, currencies, VAT rates, IBAN registry, and the compressed ECB snapshot.
- `tests/golden/` — production response fixtures.
- `deploy/` — compose, systemd, Fly, and `PRODUCTION.md`.
- `tools/` — snapshot and fixture scripts. They are not the API.

## Runtime

No database. Rates sit in memory behind `arc_swap`. A snapshot in `$DATA_DIR` is written atomically. The embedded snapshot starts the process when disk and network are both unavailable. Config is environment variables only. `TRUSTED_IP_HEADER` is the only forwarding header that is trusted.
