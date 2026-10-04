//! Replay recorded production requests against the router.
//!
//! `healthz_absent` and `readyz_absent` record the v1 404s. v2 serves those paths.

use std::collections::HashMap;
use std::path::PathBuf;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use serde::Deserialize;
use tower::ServiceExt;
use vatcomply::config::Config;
use vatcomply::http::router;
use vatcomply::state::AppState;
use wiremock::matchers::method;
use wiremock::{Mock, MockServer, ResponseTemplate};

#[derive(Deserialize)]
struct Golden {
    name: String,
    request: GoldenRequest,
    status: u16,
    headers: HashMap<String, String>,
    body: Option<String>,
    body_file: Option<String>,
}

#[derive(Deserialize)]
struct GoldenRequest {
    method: String,
    path: String,
    headers: HashMap<String, String>,
}

struct Env {
    state: AppState,
    _server: MockServer,
}

async fn env() -> Env {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .respond_with(ResponseTemplate::new(500).set_body_raw(
            include_bytes!("fixtures/vies/synthetic_fault_INVALID_INPUT.xml").as_slice(),
            "text/xml",
        ))
        .mount(&server)
        .await;
    let mut config = Config::test_default();
    config.public_base_url = "https://api.vatcomply.com".to_string();
    config.vies_url = server.uri();
    let state = AppState::load(config).expect("app state");
    Env {
        state,
        _server: server,
    }
}

fn manifest_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[tokio::test]
async fn golden_fixtures_match_production() {
    let env = env().await;
    let dir = manifest_dir().join("tests/golden");
    let mut paths: Vec<PathBuf> = std::fs::read_dir(&dir)
        .expect("golden dir")
        .map(|entry| entry.expect("entry").path())
        .filter(|path| path.extension().is_some_and(|ext| ext == "json"))
        .collect();
    paths.sort();
    let mut failures = Vec::new();
    let mut checked = 0u32;
    for path in paths {
        let name = path
            .file_stem()
            .and_then(|stem| stem.to_str())
            .unwrap_or("");
        if name == "healthz_absent" || name == "readyz_absent" {
            continue;
        }
        checked += 1;
        if let Err(error) = check_one(&env.state, &path).await {
            failures.push(format!("{name}: {error}"));
        }
    }
    assert!(
        checked >= 70,
        "expected the recorded suite, checked {checked}"
    );
    if !failures.is_empty() {
        panic!(
            "{} golden failures:\n{}",
            failures.len(),
            failures.join("\n")
        );
    }
}

async fn check_one(state: &AppState, path: &std::path::Path) -> Result<(), String> {
    let golden: Golden =
        serde_json::from_slice(&std::fs::read(path).map_err(|error| error.to_string())?)
            .map_err(|error| error.to_string())?;
    let mut builder = Request::builder()
        .method(golden.request.method.as_str())
        .uri(golden.request.path.as_str());
    for (name, value) in &golden.request.headers {
        builder = builder.header(name, value);
    }
    let request = builder
        .body(Body::empty())
        .map_err(|error| error.to_string())?;
    let response = router(state.clone())
        .oneshot(request)
        .await
        .map_err(|error| format!("router: {error}"))?;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = axum::body::to_bytes(response.into_body(), 8 * 1024 * 1024)
        .await
        .map_err(|error| error.to_string())?;
    if status.as_u16() != golden.status {
        return Err(format!(
            "status {} != {} body {}",
            status.as_u16(),
            golden.status,
            String::from_utf8_lossy(&bytes)
        ));
    }
    let expected = match (&golden.body, &golden.body_file) {
        (Some(body), _) => body.clone(),
        (None, Some(file)) => {
            let full = manifest_dir().join(file);
            let bytes = std::fs::read(&full).map_err(|error| format!("{file}: {error}"))?;
            String::from_utf8(bytes).map_err(|error| error.to_string())?
        }
        (None, None) => String::new(),
    };
    let actual = String::from_utf8(bytes.to_vec()).map_err(|error| error.to_string())?;
    if actual != expected {
        return Err(diff(&golden.name, &expected, &actual));
    }
    for (name, value) in &golden.headers {
        let got = headers
            .get(name)
            .and_then(|item| item.to_str().ok())
            .unwrap_or("");
        if got != value {
            return Err(format!("header {name}: {got:?} != {value:?}"));
        }
        if name.eq_ignore_ascii_case("content-type")
            && value.starts_with("application/json")
            && got.contains("charset")
        {
            return Err(format!("content-type has charset: {got}"));
        }
    }
    if golden.request.path == "/docs/openapi.json" {
        let got = headers
            .get("content-type")
            .and_then(|item| item.to_str().ok())
            .unwrap_or("");
        if got != "application/vnd.oai.openapi+json" {
            return Err(format!("openapi content-type {got}"));
        }
    }
    let _ = StatusCode::OK;
    Ok(())
}

fn diff(name: &str, expected: &str, actual: &str) -> String {
    let limit = 180;
    let exp = expected.chars().take(limit).collect::<String>();
    let act = actual.chars().take(limit).collect::<String>();
    format!(
        "{name} body mismatch\n expected: {exp}\n actual:   {act}\n len {} vs {}",
        expected.len(),
        actual.len()
    )
}
