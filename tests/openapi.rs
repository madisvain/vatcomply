//! The committed OpenAPI document is the oasdiff baseline.
//!
//! Regenerate with `UPDATE_OPENAPI=1 cargo test --test openapi`.

use std::path::PathBuf;

#[test]
fn openapi_matches_committed_file() {
    let generated = vatcomply::http::spec_json().expect("spec");
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("openapi.json");
    if std::env::var_os("UPDATE_OPENAPI").is_some() {
        std::fs::write(&path, &generated).expect("write openapi.json");
    }
    let committed = std::fs::read_to_string(&path).unwrap_or_default();
    assert_eq!(
        generated, committed,
        "openapi.json drifted; regenerate with UPDATE_OPENAPI=1"
    );
    for path in [
        "/rates",
        "/vat",
        "/vat_rates",
        "/geolocate",
        "/countries",
        "/currencies",
        "/iban",
        "/health",
        "/ready",
        "/healthz",
        "/readyz",
    ] {
        assert!(generated.contains(&format!("\"{path}\"")), "missing {path}");
    }
    assert!(
        !generated.contains("http://"),
        "spec must not embed http server URLs"
    );
}
