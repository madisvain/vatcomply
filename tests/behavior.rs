//! VIES, cache headers, rate limiting, geolocation, and docs behaviour.

use axum::body::Body;
use axum::extract::connect_info::MockConnectInfo;
use axum::http::Request;
use std::collections::HashMap;
use std::net::{IpAddr, SocketAddr};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tower::ServiceExt;
use vatcomply::config::Config;
use vatcomply::geo::GeoDb;
use vatcomply::http::router;
use vatcomply::state::AppState;
use vatcomply::vies::ViesService;
use wiremock::matchers::{body_string_contains, method};
use wiremock::{Mock, MockServer, ResponseTemplate};

const VALID_TRUE: &[u8] = include_bytes!("fixtures/vies/synthetic_valid_true.xml");
const VALID_FALSE: &[u8] = include_bytes!("fixtures/vies/synthetic_valid_false.xml");
const NAME_NIL: &[u8] = include_bytes!("fixtures/vies/synthetic_name_nil.xml");
const INVALID: &[u8] = include_bytes!("fixtures/vies/synthetic_fault_INVALID_INPUT.xml");
const TIMEOUT: &[u8] = include_bytes!("fixtures/vies/synthetic_fault_TIMEOUT.xml");
const UNAVAILABLE: &[u8] = include_bytes!("fixtures/vies/synthetic_fault_MS_UNAVAILABLE.xml");
const MAX_REQ: &[u8] = include_bytes!("fixtures/vies/synthetic_fault_MS_MAX_CONCURRENT_REQ.xml");
const MAX_TIME: &[u8] =
    include_bytes!("fixtures/vies/synthetic_fault_MS_MAX_CONCURRENT_REQ_TIME.xml");
const SERVICE: &[u8] = include_bytes!("fixtures/vies/synthetic_fault_SERVICE_UNAVAILABLE.xml");
const GLOBAL: &[u8] = include_bytes!("fixtures/vies/synthetic_fault_GLOBAL_MAX_CONCURRENT_REQ.xml");

struct World {
    state: AppState,
    _server: MockServer,
}

async fn world() -> World {
    let server = MockServer::start().await;
    mount_vies(&server).await;
    let mut config = Config::test_default();
    config.public_base_url = "https://api.vatcomply.com".to_string();
    config.vies_url = server.uri();
    config.metrics = true;
    config.geoip_db_path = Some(mmdb_path());
    let (state, _) = AppState::load(config).expect("state");
    World {
        state,
        _server: server,
    }
}

fn mmdb_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/geo/GeoIP2-Country-Test.mmdb")
}

fn xml(status: u16, body: &'static [u8]) -> ResponseTemplate {
    ResponseTemplate::new(status)
        .set_body_raw(body, "text/xml")
        .append_header("content-type", "text/xml")
}

async fn mount_number(server: &MockServer, national: &str, status: u16, body: &'static [u8]) {
    Mock::given(method("POST"))
        .and(body_string_contains(format!(
            "<vatNumber>{national}</vatNumber>"
        )))
        .respond_with(xml(status, body))
        .mount(server)
        .await;
}

async fn mount_vies(server: &MockServer) {
    mount_number(server, "111111111", 200, VALID_TRUE).await;
    mount_number(server, "222222222", 200, VALID_FALSE).await;
    mount_number(server, "333333333", 200, NAME_NIL).await;
    mount_number(server, "444444444", 500, INVALID).await;
    mount_number(server, "555555555", 500, TIMEOUT).await;
    mount_number(server, "100000001", 500, TIMEOUT).await;
    mount_number(server, "200000001", 200, VALID_TRUE).await;
    for (national, body) in [
        ("666666661", UNAVAILABLE),
        ("666666662", MAX_REQ),
        ("666666663", MAX_TIME),
        ("666666664", SERVICE),
        ("666666665", GLOBAL),
    ] {
        mount_number(server, national, 500, body).await;
    }
    Mock::given(method("POST"))
        .and(body_string_contains("<vatNumber>777777777</vatNumber>"))
        .respond_with(xml(200, VALID_TRUE))
        .mount(server)
        .await;
    Mock::given(method("POST"))
        .and(body_string_contains("<vatNumber>777777777</vatNumber>"))
        .respond_with(xml(500, TIMEOUT))
        .up_to_n_times(1)
        .mount(server)
        .await;
}

async fn call(
    state: &AppState,
    method_name: &str,
    path: &str,
    headers: &[(&str, &str)],
) -> (u16, HashMap<String, String>, String) {
    let mut builder = Request::builder().method(method_name).uri(path);
    for (name, value) in headers {
        builder = builder.header(*name, *value);
    }
    let request = builder.body(Body::empty()).unwrap();
    send(state, request).await
}

async fn send(state: &AppState, request: Request<Body>) -> (u16, HashMap<String, String>, String) {
    let response = router(state.clone())
        .oneshot(request)
        .await
        .expect("response");
    let status = response.status().as_u16();
    let mut headers = HashMap::new();
    for (name, value) in response.headers() {
        if let Ok(text) = value.to_str() {
            headers.insert(name.to_string(), text.to_string());
        }
    }
    let bytes = axum::body::to_bytes(response.into_body(), 8 * 1024 * 1024)
        .await
        .expect("body");
    (
        status,
        headers,
        String::from_utf8(bytes.to_vec()).expect("utf8"),
    )
}

#[tokio::test]
async fn vies_success_cache_faults_and_breaker() {
    let world = world().await;
    let (status, _, body) = call(&world.state, "GET", "/vat?vat_number=DE111111111", &[]).await;
    assert_eq!(status, 200, "{body}");
    assert_eq!(
        body,
        r#"{"valid":true,"vat_number":"100","country_code":"DE","name":"John Doe","address":"123 Main St"}"#
    );
    let hits = world._server.received_requests().await.unwrap().len();
    let (status, _, _) = call(&world.state, "GET", "/vat?vat_number=DE111111111", &[]).await;
    assert_eq!(status, 200);
    let hits_after = world._server.received_requests().await.unwrap().len();
    assert_eq!(hits_after, hits, "valid=true is cached");

    let (status, _, body) = call(&world.state, "GET", "/vat?vat_number=DE222222222", &[]).await;
    assert_eq!(status, 200, "{body}");
    assert!(body.contains(r#""valid":false"#));
    assert!(body.contains(r#""name":"---"#));
    let false_hits = world._server.received_requests().await.unwrap().len();
    let _ = call(&world.state, "GET", "/vat?vat_number=DE222222222", &[]).await;
    let false_after = world._server.received_requests().await.unwrap().len();
    assert!(false_after > false_hits, "valid=false is not cached");

    let (status, _, body) = call(&world.state, "GET", "/vat?vat_number=DE333333333", &[]).await;
    assert_eq!(status, 200, "{body}");
    assert!(body.contains(r#""name":null"#));

    let before = world._server.received_requests().await.unwrap().len();
    let (status, _, body) = call(&world.state, "GET", "/vat?vat_number=DE444444444", &[]).await;
    assert_eq!(status, 400, "{body}");
    assert_eq!(body, r#"{"detail":"INVALID_INPUT"}"#);
    let after = world._server.received_requests().await.unwrap().len();
    assert_eq!(after - before, 1, "permanent faults are not retried");

    let before = after;
    let (status, headers, body) =
        call(&world.state, "GET", "/vat?vat_number=DE555555555", &[]).await;
    assert_eq!(status, 503, "{body}");
    assert_eq!(body, r#"{"detail":"TIMEOUT"}"#);
    assert_eq!(headers.get("retry-after").map(String::as_str), Some("5"));
    assert_eq!(
        headers.get("cache-control").map(String::as_str),
        Some("no-store")
    );
    let after = world._server.received_requests().await.unwrap().len();
    assert_eq!(after - before, 3, "transient faults retry twice more");

    let (status, headers, body) =
        call(&world.state, "GET", "/vat?vat_number=DE777777777", &[]).await;
    assert_eq!(status, 200, "{body}");
    assert_eq!(
        headers.get("cache-control").map(String::as_str),
        Some("private, no-store")
    );

    for number in ["661", "662", "663", "664", "665"] {
        let path = format!("/vat?vat_number=DE666666{number}");
        let (status, headers, body) = call(&world.state, "GET", &path, &[]).await;
        assert_eq!(status, 503, "{number} {body}");
        assert_eq!(headers.get("retry-after").map(String::as_str), Some("5"));
        assert!(!body.contains("retry_after"), "{body}");
    }

    let before = world._server.received_requests().await.unwrap().len();
    for _ in 0..5 {
        let (status, _, body) = call(&world.state, "GET", "/vat?vat_number=FR100000001", &[]).await;
        assert_eq!(status, 503, "{body}");
    }
    let opened = world._server.received_requests().await.unwrap().len();
    assert_eq!(opened - before, 15);
    let (status, _, body) = call(&world.state, "GET", "/vat?vat_number=FR100000002", &[]).await;
    assert_eq!(status, 503, "{body}");
    assert_eq!(body, r#"{"detail":"MS_UNAVAILABLE"}"#);
    let after = world._server.received_requests().await.unwrap().len();
    assert_eq!(after, opened, "open breaker does not call VIES");
    let (status, _, body) = call(&world.state, "GET", "/vat?vat_number=ES200000001", &[]).await;
    assert_eq!(status, 200, "{body}");
}

#[tokio::test]
async fn breaker_recovers_after_cooldown() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .respond_with(xml(500, TIMEOUT))
        .up_to_n_times(15)
        .mount(&server)
        .await;
    Mock::given(method("POST"))
        .respond_with(xml(200, VALID_TRUE))
        .mount(&server)
        .await;
    let mut config = Config::test_default();
    config.vies_url = server.uri();
    let clock = Arc::new(AtomicU64::new(1_000));
    let vies = ViesService::new(&config).unwrap().with_clock({
        let clock = clock.clone();
        Arc::new(move || clock.load(Ordering::Relaxed))
    });
    for _ in 0..5 {
        let error = vies.check("NL123456789").await.unwrap_err();
        assert!(matches!(
            error,
            vatcomply::vies::ViesFailure::Unavailable(_)
        ));
    }
    let error = vies.check("NL123456780").await.unwrap_err();
    assert!(matches!(error, vatcomply::vies::ViesFailure::BreakerOpen));
    clock.store(31_000, Ordering::Relaxed);
    let ok = vies.check("NL123456781").await.expect("half-open trial");
    assert!(ok.valid);
    let ok = vies.check("NL999999999").await.expect("closed");
    assert!(ok.valid);
}

#[tokio::test]
async fn cache_headers_etag_and_cors() {
    let world = world().await;
    let (status, headers, _body) = call(&world.state, "GET", "/rates", &[]).await;
    assert_eq!(status, 200);
    assert_eq!(
        headers.get("cache-control").map(String::as_str),
        Some("public, max-age=300")
    );
    let etag = headers.get("etag").cloned().expect("etag");
    assert!(etag.starts_with('"') && etag.ends_with('"'));
    let (status, headers, empty) = call(
        &world.state,
        "GET",
        "/rates",
        &[("If-None-Match", etag.as_str())],
    )
    .await;
    assert_eq!(status, 304);
    assert_eq!(empty, "");
    assert_eq!(headers.get("etag").map(String::as_str), Some(etag.as_str()));

    let (_, headers, _) = call(&world.state, "GET", "/rates?date=2018-10-12", &[]).await;
    assert_eq!(
        headers.get("cache-control").map(String::as_str),
        Some("public, max-age=86400")
    );
    let (_, headers, _) = call(&world.state, "GET", "/rates?date=", &[]).await;
    assert_eq!(
        headers.get("cache-control").map(String::as_str),
        Some("public, max-age=300")
    );
    let (_, headers, _) = call(&world.state, "GET", "/countries", &[]).await;
    assert_eq!(
        headers.get("cache-control").map(String::as_str),
        Some("public, max-age=86400")
    );
    let (_, headers, _) = call(&world.state, "GET", "/vat?vat_number=123", &[]).await;
    assert_eq!(
        headers.get("cache-control").map(String::as_str),
        Some("no-store")
    );
    let (_, headers, _) = call(&world.state, "GET", "/nope", &[]).await;
    assert_eq!(
        headers.get("cache-control").map(String::as_str),
        Some("no-store")
    );
    assert_eq!(
        headers
            .get("access-control-allow-origin")
            .map(String::as_str),
        Some("*")
    );

    let (status, headers, _) = call(&world.state, "GET", "/docs/openapi.json", &[]).await;
    assert_eq!(status, 200);
    assert_eq!(
        headers.get("content-type").map(String::as_str),
        Some("application/vnd.oai.openapi+json")
    );
    let (status, headers, page) = call(&world.state, "GET", "/docs", &[]).await;
    assert_eq!(status, 200);
    assert!(page.contains("src=\"/docs/scalar.js\""));
    assert!(!page.contains("src=\"http"));
    assert!(!page.contains("href=\"http"));
    assert!(!page.contains("jsdelivr"));
    assert!(page.find("api-reference").unwrap() < page.find("scalar.js").unwrap());
    let _ = headers;

    let (status, headers, body) = call(&world.state, "GET", "/readyz", &[]).await;
    assert_eq!(status, 200, "{body}");
    assert!(body.contains(r#""source":"embedded""#), "{body}");
    assert_eq!(
        headers.get("cache-control").map(String::as_str),
        Some("no-store")
    );

    let (status, headers, body) = call(&world.state, "GET", "/metrics", &[]).await;
    assert_eq!(status, 200, "{body}");
    assert_eq!(
        headers.get("content-type").map(String::as_str),
        Some("text/plain; version=0.0.4")
    );
    assert!(body.contains("http_requests_total"));
}

#[tokio::test]
async fn rate_limit_matches_v1_and_skips_health() {
    let mut config = Config::test_default();
    config.rate_limit_rps = 2;
    config.rate_limit_burst = 4;
    let (state, _) = AppState::load(config).unwrap();
    let app = router(state.clone());
    let mut saw_limit = false;
    for index in 0..5 {
        let request = Request::builder()
            .uri("/rates")
            .header("X-Forwarded-For", format!("203.0.113.{index}"))
            .body(Body::empty())
            .unwrap();
        let response = app.clone().oneshot(request).await.unwrap();
        let status = response.status().as_u16();
        let headers = response.headers().clone();
        let bytes = axum::body::to_bytes(response.into_body(), 1024 * 1024)
            .await
            .unwrap();
        let body = String::from_utf8(bytes.to_vec()).unwrap();
        let header = |name: &str| {
            headers
                .get(name)
                .and_then(|value| value.to_str().ok())
                .map(str::to_string)
        };
        if index < 4 {
            assert_eq!(status, 200, "{body}");
            assert!(header("x-ratelimit-limit").is_none());
        } else {
            saw_limit = true;
            assert_eq!(status, 429, "{body}");
            assert_eq!(
                body,
                r#"{"detail":"Rate limit exceeded. Try again in 1 seconds.","retry_after":1}"#
            );
            assert_eq!(header("retry-after").as_deref(), Some("1"));
            assert_eq!(header("x-ratelimit-limit").as_deref(), Some("2"));
            assert_eq!(header("cache-control").as_deref(), Some("no-store"));
        }
    }
    assert!(saw_limit);
    for path in ["/health", "/healthz", "/ready", "/readyz"] {
        for _ in 0..6 {
            let request = Request::builder().uri(path).body(Body::empty()).unwrap();
            let response = app.clone().oneshot(request).await.unwrap();
            assert_eq!(response.status().as_u16(), 200, "{path}");
        }
    }
}

#[tokio::test]
async fn geodb_fallback_and_header_wins() {
    let db = GeoDb::open(&mmdb_path()).unwrap();
    let candidates = [
        "81.2.69.142",
        "2.125.160.216",
        "89.160.20.128",
        "216.160.83.56",
        "1.1.1.1",
        "8.8.8.8",
    ];
    let mut found = None;
    for text in candidates {
        let ip: IpAddr = text.parse().unwrap();
        if let Some(code) = db.iso_code(ip) {
            found = Some((ip, code));
            break;
        }
    }
    let (ip, code) = found.expect("sample address in the MaxMind test database");
    let world = world().await;
    let mut request = Request::builder()
        .uri("/geolocate")
        .body(Body::empty())
        .unwrap();
    request
        .extensions_mut()
        .insert(MockConnectInfo(SocketAddr::new(ip, 9)));
    let (status, _, body) = send(&world.state, request).await;
    assert!(status == 200 || status == 404, "{status} {body}");
    assert!(body.contains(&code), "{body}");
    assert!(body.contains(r#""ip":null"#) || status == 404, "{body}");

    let mut request = Request::builder()
        .uri("/geolocate")
        .header("CF-IPCountry", "EE")
        .header("CF-Connecting-IP", "203.0.113.10")
        .body(Body::empty())
        .unwrap();
    request
        .extensions_mut()
        .insert(MockConnectInfo(SocketAddr::new(ip, 9)));
    let (status, _, body) = send(&world.state, request).await;
    assert_eq!(status, 200, "{body}");
    assert!(body.contains(r#""country_code":"EE""#), "{body}");
    assert!(body.contains(r#""ip":"203.0.113.10""#), "{body}");
}
