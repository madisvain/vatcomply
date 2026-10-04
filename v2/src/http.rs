//! Routes, caching, CORS, and the rate limiter.
//!
//! `HEAD` is a 404 before routing so axum does not turn it into `GET`.
//! `OPTIONS` is 204 with the production CORS headers. A single trailing
//! slash is removed and the query string is kept.

use std::collections::HashMap;
use std::convert::Infallible;
use std::net::{IpAddr, SocketAddr};
use std::sync::Arc;
use std::task::{Context, Poll};
use std::time::Duration;

use axum::body::Body;
use axum::extract::{ConnectInfo, Request, State};
use axum::http::header::{self, HeaderName, HeaderValue};
use axum::http::{HeaderMap, Method, StatusCode, Uri};
use axum::middleware::{from_fn, Next};
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use axum::Router;
use bytes::Bytes;
use prometheus::Encoder;
use tower::Service;
use tower_governor::governor::GovernorConfigBuilder;
use tower_governor::key_extractor::KeyExtractor;
use tower_governor::{GovernorError, GovernorLayer};
use tower_http::catch_panic::CatchPanicLayer;
use tower_http::compression::CompressionLayer;
use tower_http::timeout::TimeoutLayer;
use tower_http::trace::TraceLayer;
use utoipa::openapi::{Info, OpenApi, Paths};
use utoipa::IntoParams;
use utoipa_axum::router::OpenApiRouter;
use utoipa_axum::routes;

use crate::config::Config;
use crate::data;
use crate::date::{unix_now, Date};
use crate::error::ApiError;
use crate::query;
use crate::rates::book::{self, RatesQuery};
use crate::rates::snapshot;
use crate::state::{AppState, Metrics};
use crate::vies::{self, ViesFailure};

const SCALAR_JS: &str = include_str!("../assets/scalar.js");
const GB_DETAIL: &str = "As of 01/01/2021, the VoW service to validate UK (GB) VAT numbers ceased to exist while a new service to validate VAT numbers of businesses operating under the Protocol on Ireland and Northern Ireland appeared. These VAT numbers are starting with the \"XI\" prefix.";
const VAT_FORMAT: &str = "Invalid VAT number format. Expected format: Two-letter country code followed by 8-12 digits or letters.";
const GEO_MISSING: &str =
    "Country code not received from CDN headers (CF-IPCountry or Cdn-RequestCountryCode).";

pub fn spec_json() -> Result<String, String> {
    let mut router = business_router().merge(probe_router());
    router
        .to_openapi()
        .to_json()
        .map_err(|error| format!("openapi: {error}"))
}

pub fn docs_page(spec: &str) -> String {
    let spec = spec.replace('<', "\\u003c");
    format!(
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Vatcomply API</title></head><body><script id=\"api-reference\" type=\"application/json\">{spec}</script><script src=\"/docs/scalar.js\"></script></body></html>"
    )
}

/// Router plus a pre-routing rewrite that drops one trailing slash.
///
/// `Router::layer` runs after matching, so the rewrite has to wrap the router.
#[derive(Clone)]
pub struct AppService {
    inner: Router,
}

impl Service<Request> for AppService {
    type Response = Response;
    type Error = Infallible;
    type Future = <Router as Service<Request>>::Future;

    fn poll_ready(&mut self, cx: &mut Context<'_>) -> Poll<Result<(), Self::Error>> {
        <Router as Service<Request>>::poll_ready(&mut self.inner, cx)
    }

    fn call(&mut self, mut request: Request) -> Self::Future {
        if let Some(uri) = strip_slash(request.uri()) {
            *request.uri_mut() = uri;
        }
        <Router as Service<Request>>::call(&mut self.inner, request)
    }
}

pub fn router(state: AppState) -> AppService {
    let metrics = state.metrics.clone();
    let limited = limit(api_router(), &state.config);
    let inner = Router::new()
        .merge(health_router())
        .merge(docs_router())
        .merge(limited)
        .fallback(not_found)
        .method_not_allowed_fallback(not_found)
        .layer(from_fn(move |request, next| {
            let metrics = metrics.clone();
            async move { cache_and_count(metrics, request, next).await }
        }))
        .layer(from_fn(ingress))
        .layer(CompressionLayer::new())
        .layer(TimeoutLayer::with_status_code(
            StatusCode::REQUEST_TIMEOUT,
            Duration::from_secs(30),
        ))
        .layer(CatchPanicLayer::custom(panic_response))
        .layer(
            TraceLayer::new_for_http()
                .make_span_with(|request: &Request| {
                    let query = request.uri().query().map(query::redact).unwrap_or_default();
                    tracing::info_span!(
                        "request",
                        method = %request.method(),
                        path = %request.uri().path(),
                        query = %query,
                    )
                })
                .on_request(())
                .on_response(
                    |response: &Response, latency: Duration, span: &tracing::Span| {
                        tracing::info!(
                            parent: span,
                            status = response.status().as_u16(),
                            latency_ms = latency.as_millis() as u64,
                            "request"
                        );
                    },
                ),
        )
        .with_state(state);
    AppService { inner }
}

fn api_info() -> Info {
    let mut info = Info::new("Vatcomply API", "1.0.0");
    info.description =
        Some("API for automated VAT compliance and currency conversion.".to_string());
    info
}

fn business_router() -> OpenApiRouter<AppState> {
    OpenApiRouter::with_openapi(OpenApi::new(api_info(), Paths::new()))
        .routes(routes!(root))
        .routes(routes!(countries))
        .routes(routes!(currencies))
        .routes(routes!(geolocate))
        .routes(routes!(iban))
        .routes(routes!(vat))
        .routes(routes!(vat_rates))
        .routes(routes!(rates))
}

fn probe_router() -> OpenApiRouter<AppState> {
    OpenApiRouter::with_openapi(OpenApi::new(api_info(), Paths::new()))
        .routes(routes!(health))
        .routes(routes!(ready))
        .routes(routes!(healthz))
        .routes(routes!(readyz))
}

fn api_router() -> Router<AppState> {
    business_router().split_for_parts().0
}

fn health_router() -> Router<AppState> {
    probe_router()
        .split_for_parts()
        .0
        .route("/metrics", get(metrics))
}

fn docs_router() -> Router<AppState> {
    Router::new()
        .route("/docs", get(docs))
        .route("/docs/scalar.js", get(scalar_js))
        .route("/openapi.json", get(openapi_json))
        .route("/docs/openapi.json", get(openapi_vnd))
}

fn limit(router: Router<AppState>, config: &Config) -> Router<AppState> {
    let Some((period, burst, limit_value)) = quota(config) else {
        return router;
    };
    let header = config
        .trusted_ip_header
        .as_deref()
        .and_then(|name| HeaderName::from_bytes(name.as_bytes()).ok());
    let mut builder = GovernorConfigBuilder::default();
    builder.period(period).burst_size(burst);
    let mut builder = builder.key_extractor(ClientIpKey { header });
    let Some(governor) = builder.finish() else {
        return router;
    };
    let limit_header = HeaderValue::from_str(&limit_value.to_string())
        .unwrap_or_else(|_| HeaderValue::from_static("1"));
    router.layer(
        GovernorLayer::new(governor)
            .error_handler(move |error| rate_limited(error, limit_header.clone()).into_response()),
    )
}

fn quota(config: &Config) -> Option<(Duration, u32, u32)> {
    let burst = config.rate_limit_burst.max(1);
    if config.rate_limit_rps > 0 {
        let millis = (1000 / u64::from(config.rate_limit_rps)).max(1);
        Some((Duration::from_millis(millis), burst, config.rate_limit_rps))
    } else if config.rate_limit_per_min > 0 {
        let millis = (60_000 / u64::from(config.rate_limit_per_min)).max(1);
        Some((
            Duration::from_millis(millis),
            burst,
            config.rate_limit_per_min,
        ))
    } else {
        None
    }
}

fn rate_limited(error: GovernorError, limit_header: HeaderValue) -> ApiError {
    match error {
        GovernorError::TooManyRequests { .. } => ApiError {
            status: StatusCode::TOO_MANY_REQUESTS,
            detail: "Rate limit exceeded. Try again in 1 seconds.".to_string(),
            body_retry_after: Some(1),
            retry_after_header: Some(HeaderValue::from_static("1")),
            ratelimit_limit: Some(limit_header),
        },
        _ => ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "Internal Server Error"),
    }
}

#[derive(Clone)]
struct ClientIpKey {
    header: Option<HeaderName>,
}

impl KeyExtractor for ClientIpKey {
    type Key = String;

    fn extract<T>(&self, request: &axum::http::Request<T>) -> Result<Self::Key, GovernorError> {
        if let Some(name) = &self.header {
            if let Some(value) = request.headers().get(name) {
                if let Ok(text) = value.to_str() {
                    let text = text.trim();
                    if !text.is_empty() {
                        return Ok(text.to_string());
                    }
                }
            }
        }
        if let Some(info) = request.extensions().get::<ConnectInfo<SocketAddr>>() {
            return Ok(info.ip().to_string());
        }
        if let Some(info) = request
            .extensions()
            .get::<axum::extract::connect_info::MockConnectInfo<SocketAddr>>()
        {
            return Ok(info.0.ip().to_string());
        }
        Ok("unknown".to_string())
    }
}

fn panic_response(_: Box<dyn std::any::Any + Send>) -> Response {
    let mut response = Response::new(Body::from(r#"{"detail":"Internal Server Error"}"#));
    *response.status_mut() = StatusCode::INTERNAL_SERVER_ERROR;
    let headers = response.headers_mut();
    headers.insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/json"),
    );
    headers.insert(header::CACHE_CONTROL, HeaderValue::from_static("no-store"));
    response
}

async fn ingress(request: Request, next: Next) -> Response {
    if request.method() == Method::OPTIONS {
        return options_response();
    }
    if request.method() == Method::HEAD {
        return head_not_found();
    }
    let mut response = next.run(request).await;
    response.headers_mut().insert(
        header::ACCESS_CONTROL_ALLOW_ORIGIN,
        HeaderValue::from_static("*"),
    );
    response
}

fn options_response() -> Response {
    let mut response = Response::new(Body::empty());
    *response.status_mut() = StatusCode::NO_CONTENT;
    let headers = response.headers_mut();
    headers.insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/json"),
    );
    headers.insert(header::ALLOW, HeaderValue::from_static("GET, OPTIONS"));
    headers.insert(
        header::ACCESS_CONTROL_ALLOW_ORIGIN,
        HeaderValue::from_static("*"),
    );
    headers.insert(
        header::ACCESS_CONTROL_ALLOW_METHODS,
        HeaderValue::from_static("GET, POST, PUT, PATCH, DELETE, OPTIONS"),
    );
    headers.insert(
        header::ACCESS_CONTROL_ALLOW_HEADERS,
        HeaderValue::from_static("Content-Type, Authorization"),
    );
    response
}

fn head_not_found() -> Response {
    let mut response = Response::new(Body::empty());
    *response.status_mut() = StatusCode::NOT_FOUND;
    response.headers_mut().insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/json"),
    );
    response.headers_mut().insert(
        header::ACCESS_CONTROL_ALLOW_ORIGIN,
        HeaderValue::from_static("*"),
    );
    response
}

fn strip_slash(uri: &Uri) -> Option<Uri> {
    let path = uri.path();
    if path.len() <= 1 || !path.ends_with('/') {
        return None;
    }
    let path = &path[..path.len() - 1];
    let path_and_query = match uri.query() {
        Some(query) => format!("{path}?{query}"),
        None => path.to_string(),
    };
    let mut parts = uri.clone().into_parts();
    parts.path_and_query = path_and_query.parse().ok();
    Uri::from_parts(parts).ok()
}

async fn cache_and_count(metrics: Option<Arc<Metrics>>, request: Request, next: Next) -> Response {
    let path = request.uri().path().to_string();
    let query = request.uri().query().map(str::to_string);
    let inm = request.headers().get(header::IF_NONE_MATCH).cloned();
    let response = next.run(request).await;
    if let Some(metrics) = &metrics {
        let status = response.status().as_u16().to_string();
        metrics.requests.with_label_values(&[&status]).inc();
    }
    apply_cache(response, &path, query.as_deref(), inm.as_ref()).await
}

async fn apply_cache(
    response: Response,
    path: &str,
    query: Option<&str>,
    inm: Option<&HeaderValue>,
) -> Response {
    let (mut parts, body) = response.into_parts();
    let bytes = match axum::body::to_bytes(body, 8 * 1024 * 1024).await {
        Ok(bytes) => bytes,
        Err(_) => {
            return ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "Internal Server Error")
                .into_response();
        }
    };
    let policy = cache_control(path, query, parts.status);
    parts
        .headers
        .insert(header::CACHE_CONTROL, HeaderValue::from_static(policy));
    if parts.status.is_success() && !policy.contains("no-store") {
        let etag = format!("\"{}\"", snapshot::sha256_hex(&bytes));
        if let Ok(value) = HeaderValue::from_str(&etag) {
            if etag_matches(inm, &etag) {
                parts.status = StatusCode::NOT_MODIFIED;
                parts.headers.insert(header::ETAG, value);
                return Response::from_parts(parts, Body::empty());
            }
            parts.headers.insert(header::ETAG, value);
        }
    }
    Response::from_parts(parts, Body::from(bytes))
}

fn etag_matches(header: Option<&HeaderValue>, etag: &str) -> bool {
    let Some(header) = header else {
        return false;
    };
    let Ok(text) = header.to_str() else {
        return false;
    };
    text.split(',').any(|part| part.trim() == etag)
}

fn cache_control(path: &str, query: Option<&str>, status: StatusCode) -> &'static str {
    if !status.is_success() {
        return "no-store";
    }
    let path = if path.len() > 1 && path.ends_with('/') {
        &path[..path.len() - 1]
    } else {
        path
    };
    match path {
        "/vat" | "/geolocate" | "/iban" => "private, no-store",
        "/health" | "/healthz" | "/ready" | "/readyz" | "/metrics" => "no-store",
        "/" => "public, max-age=60",
        "/rates" => {
            let dated = query::last(query)
                .get("date")
                .is_some_and(|value| !value.is_empty());
            if dated {
                "public, max-age=86400"
            } else {
                "public, max-age=300"
            }
        }
        "/countries" | "/currencies" | "/vat_rates" | "/openapi.json" | "/docs"
        | "/docs/scalar.js" | "/docs/openapi.json" => "public, max-age=86400",
        _ => "no-store",
    }
}

fn json_response(status: StatusCode, body: impl Into<Bytes>) -> Response {
    let mut response = Response::new(Body::from(body.into()));
    *response.status_mut() = status;
    response.headers_mut().insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/json"),
    );
    response
}

async fn not_found() -> Response {
    json_response(StatusCode::NOT_FOUND, r#"{"detail":"Not Found"}"#)
}

fn params(uri: &Uri) -> HashMap<String, String> {
    query::last(uri.query())
}

fn optional<'a>(map: &'a HashMap<String, String>, name: &str) -> Option<&'a str> {
    map.get(name).map(String::as_str)
}

fn required<'a>(map: &'a HashMap<String, String>, name: &str) -> Result<&'a str, ApiError> {
    optional(map, name).ok_or_else(|| {
        ApiError::new(
            StatusCode::UNPROCESSABLE_ENTITY,
            format!("Missing required query parameter: {name}"),
        )
    })
}

fn header_text(headers: &HeaderMap, name: &str) -> Option<String> {
    let name = HeaderName::from_bytes(name.as_bytes()).ok()?;
    let text = headers.get(name)?.to_str().ok()?.trim();
    if text.is_empty() {
        None
    } else {
        Some(text.to_string())
    }
}

fn peer_ip(request: &Request) -> Option<IpAddr> {
    if let Some(info) = request.extensions().get::<ConnectInfo<SocketAddr>>() {
        return Some(info.ip());
    }
    request
        .extensions()
        .get::<axum::extract::connect_info::MockConnectInfo<SocketAddr>>()
        .map(|info| info.0.ip())
}

#[derive(IntoParams)]
#[allow(dead_code)]
struct RatesParams {
    /// Base currency. Defaults to EUR.
    base: Option<String>,
    /// Comma-separated currency codes.
    symbols: Option<String>,
    /// Historical date, YYYY-MM-DD. Empty means today.
    date: Option<String>,
}

#[derive(IntoParams)]
#[allow(dead_code)]
struct CountriesParams {
    /// Search by country name, ISO2, or ISO3.
    search: Option<String>,
    /// Filter by region.
    region: Option<String>,
    /// Filter by subregion.
    subregion: Option<String>,
    /// Filter by currency code.
    currency: Option<String>,
}

#[derive(IntoParams)]
#[allow(dead_code)]
struct SearchParam {
    /// Search by code or name.
    search: Option<String>,
}

#[derive(IntoParams)]
#[allow(dead_code)]
struct VatRatesParams {
    /// EU member state code. Greece is EL.
    country_code: Option<String>,
}

#[derive(IntoParams)]
#[allow(dead_code)]
struct VatParam {
    /// VAT number, country prefix plus 8-12 letters or digits.
    vat_number: String,
}

#[derive(IntoParams)]
#[allow(dead_code)]
struct IbanParam {
    /// IBAN to validate.
    iban: String,
}

#[utoipa::path(
    get,
    path = "/",
    responses((status = 200, description = "Service description"))
)]
async fn root(State(state): State<AppState>) -> Response {
    json_response(StatusCode::OK, root_body(&state.config.public_base_url))
}

fn root_body(base: &str) -> String {
    let base = base.trim_end_matches('/');
    format!(
        "{{\"name\":\"VATComply API\",\"version\":\"1.0.0\",\"status\":\"operational\",\"description\":\"VAT validation API, geolocation tools, and ECB exchange rates\",\"documentation\":\"{base}/docs\",\"openapi\":\"{base}/docs/openapi.json\",\"endpoints\":{{\"countries\":\"{base}/countries\",\"currencies\":\"{base}/currencies\",\"geolocate\":\"{base}/geolocate\",\"iban\":\"{base}/iban\",\"vat\":\"{base}/vat\",\"vat_rates\":\"{base}/vat_rates\",\"rates\":\"{base}/rates\"}},\"contact\":\"support@vatcomply.com\"}}"
    )
}

#[utoipa::path(
    get,
    path = "/countries",
    params(CountriesParams),
    responses((status = 200, description = "Countries"))
)]
async fn countries(State(state): State<AppState>, uri: Uri) -> Response {
    let map = params(&uri);
    json_response(
        StatusCode::OK,
        state.static_data.countries(
            optional(&map, "search"),
            optional(&map, "region"),
            optional(&map, "subregion"),
            optional(&map, "currency"),
        ),
    )
}

#[utoipa::path(
    get,
    path = "/currencies",
    params(SearchParam),
    responses((status = 200, description = "Currencies"))
)]
async fn currencies(State(state): State<AppState>, uri: Uri) -> Response {
    let map = params(&uri);
    json_response(
        StatusCode::OK,
        state.static_data.currencies(optional(&map, "search")),
    )
}

#[utoipa::path(
    get,
    path = "/vat_rates",
    params(VatRatesParams),
    responses((status = 200, description = "EU VAT rates"))
)]
async fn vat_rates(State(state): State<AppState>, uri: Uri) -> Response {
    let map = params(&uri);
    json_response(
        StatusCode::OK,
        state.static_data.vat_rates(optional(&map, "country_code")),
    )
}

#[utoipa::path(
    get,
    path = "/rates",
    params(RatesParams),
    responses(
        (status = 200, description = "Exchange rates"),
        (status = 400, description = "Invalid currency or date"),
        (status = 404, description = "No rate for that date")
    )
)]
async fn rates(State(state): State<AppState>, uri: Uri) -> Result<Response, ApiError> {
    let map = params(&uri);
    let book = state.rates.load_full();
    let body = book::answer(
        &book,
        RatesQuery {
            base: optional(&map, "base"),
            symbols: optional(&map, "symbols"),
            date_raw: optional(&map, "date"),
        },
        state.config.today(),
    )?;
    Ok(json_response(StatusCode::OK, body))
}

#[utoipa::path(
    get,
    path = "/vat",
    params(VatParam),
    responses(
        (status = 200, description = "VIES result"),
        (status = 400, description = "Invalid number or permanent VIES fault"),
        (status = 422, description = "Missing vat_number"),
        (status = 503, description = "VIES unavailable")
    )
)]
async fn vat(State(state): State<AppState>, uri: Uri) -> Result<Response, ApiError> {
    let map = params(&uri);
    let vat_number = required(&map, "vat_number")?;
    if !vies::valid_vat_format(vat_number) {
        return Err(ApiError::new(StatusCode::BAD_REQUEST, VAT_FORMAT));
    }
    if vat_number.starts_with("GB") {
        return Err(ApiError::new(StatusCode::BAD_REQUEST, GB_DETAIL));
    }
    match state.vies.check(vat_number).await {
        Ok(body) => Ok(json_response(StatusCode::OK, vies::vat_json(&body))),
        Err(ViesFailure::BadRequest(detail)) => Err(ApiError::new(StatusCode::BAD_REQUEST, detail)),
        Err(ViesFailure::Unavailable(detail)) => Err(vies_unavailable(detail)),
        Err(ViesFailure::BreakerOpen) => Err(vies_unavailable("MS_UNAVAILABLE".to_string())),
    }
}

fn vies_unavailable(detail: String) -> ApiError {
    ApiError {
        status: StatusCode::SERVICE_UNAVAILABLE,
        detail,
        body_retry_after: None,
        retry_after_header: Some(HeaderValue::from_static("5")),
        ratelimit_limit: None,
    }
}

#[utoipa::path(
    get,
    path = "/iban",
    params(IbanParam),
    responses(
        (status = 200, description = "Valid IBAN"),
        (status = 400, description = "Invalid IBAN"),
        (status = 422, description = "Missing iban")
    )
)]
async fn iban(State(state): State<AppState>, uri: Uri) -> Result<Response, ApiError> {
    let map = params(&uri);
    let value = required(&map, "iban")?;
    Ok(json_response(StatusCode::OK, state.iban.answer(value)?))
}

#[utoipa::path(
    get,
    path = "/geolocate",
    responses(
        (status = 200, description = "Country for the CDN header"),
        (status = 404, description = "Country missing or unknown")
    )
)]
async fn geolocate(State(state): State<AppState>, request: Request) -> Result<Response, ApiError> {
    let headers = request.headers();
    let mut country = None;
    for name in &state.config.geo_country_headers {
        if let Some(value) = header_text(headers, name) {
            country = Some(value.to_uppercase());
            break;
        }
    }
    if country.is_none() {
        if let Some(db) = &state.geo {
            let ip = lookup_ip(&state.config, headers, peer_ip(&request));
            if let Some(ip) = ip {
                country = db.iso_code(ip);
            }
        }
    }
    let Some(code) = country else {
        return Err(ApiError::new(StatusCode::NOT_FOUND, GEO_MISSING));
    };
    let Some(slice) = state.static_data.country_slice(&code) else {
        return Err(ApiError::new(
            StatusCode::NOT_FOUND,
            format!("Data for country code `{code}` not found."),
        ));
    };
    let ip = header_text(headers, "CF-Connecting-IP");
    let body = data::geolocate_body(slice, &code, ip.as_deref())
        .map_err(|_| ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "Internal Server Error"))?;
    Ok(json_response(StatusCode::OK, body))
}

fn lookup_ip(config: &Config, headers: &HeaderMap, peer: Option<IpAddr>) -> Option<IpAddr> {
    if let Some(name) = &config.trusted_ip_header {
        if let Some(text) = header_text(headers, name) {
            if let Ok(ip) = text.parse() {
                return Some(ip);
            }
        }
    }
    peer
}

#[utoipa::path(get, path = "/health", responses((status = 200, description = "Process is up")))]
async fn health() -> Response {
    json_response(StatusCode::OK, r#"{"status":"ok"}"#)
}

#[utoipa::path(get, path = "/healthz", responses((status = 200, description = "Process is up")))]
async fn healthz() -> Response {
    json_response(StatusCode::OK, r#"{"status":"ok"}"#)
}

#[utoipa::path(
    get,
    path = "/ready",
    responses((status = 200, description = "Legacy readiness shim"))
)]
async fn ready() -> Response {
    json_response(
        StatusCode::OK,
        r#"{"status":"healthy","checks":{"check_database":{"healthy":true,"message":"Database connection OK"}}}"#,
    )
}

#[utoipa::path(
    get,
    path = "/readyz",
    responses((status = 200, description = "Rates loaded"))
)]
async fn readyz(State(state): State<AppState>) -> Response {
    let book = state.rates.load_full();
    json_response(
        StatusCode::OK,
        readyz_body(&book, &state.vies.open_breakers()),
    )
}

fn readyz_body(
    book: &crate::rates::book::RateBook,
    breakers: &std::collections::BTreeMap<String, String>,
) -> String {
    let date = book
        .latest_date()
        .map(|day| day.to_string())
        .unwrap_or_default();
    let age = book
        .latest_date()
        .map(|day: Date| day.age_secs(unix_now()))
        .unwrap_or(0);
    let mut body = String::from("{\"status\":\"ok\",\"rates_date\":");
    push_json(&mut body, &date);
    body.push_str(",\"rates_age_secs\":");
    body.push_str(&age.to_string());
    body.push_str(",\"source\":");
    push_json(&mut body, book.source.as_str());
    body.push_str(",\"fetched_at\":");
    push_json(&mut body, &book.fetched_at);
    body.push_str(",\"breakers\":{");
    for (index, (country, name)) in breakers.iter().enumerate() {
        if index > 0 {
            body.push(',');
        }
        push_json(&mut body, country);
        body.push(':');
        push_json(&mut body, name);
    }
    body.push_str("}}");
    body
}

fn push_json(out: &mut String, value: &str) {
    out.push_str(&serde_json::to_string(value).unwrap_or_else(|_| "\"\"".to_string()));
}

async fn metrics(State(state): State<AppState>) -> Response {
    let Some(metrics) = &state.metrics else {
        return not_found().await;
    };
    let families = metrics.registry.gather();
    let mut buffer = Vec::new();
    let encoder = prometheus::TextEncoder::new();
    if encoder.encode(&families, &mut buffer).is_err() {
        return ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "Internal Server Error")
            .into_response();
    }
    let mut response = Response::new(Body::from(buffer));
    response.headers_mut().insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("text/plain; version=0.0.4"),
    );
    response
}

async fn docs(State(state): State<AppState>) -> Response {
    let mut response = Response::new(Body::from(state.docs_html.clone()));
    response.headers_mut().insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("text/html; charset=utf-8"),
    );
    response
}

async fn scalar_js() -> Response {
    let mut response = Response::new(Body::from(SCALAR_JS));
    response.headers_mut().insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("text/javascript"),
    );
    response
}

async fn openapi_json(State(state): State<AppState>) -> Response {
    json_response(StatusCode::OK, state.openapi.clone())
}

async fn openapi_vnd(State(state): State<AppState>) -> Response {
    let mut response = json_response(StatusCode::OK, state.openapi.clone());
    response.headers_mut().insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/vnd.oai.openapi+json"),
    );
    response
}
