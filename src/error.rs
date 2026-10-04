//! `{"detail": ...}` errors. Production never uses an `error` field.

use axum::http::header::{self, HeaderName, HeaderValue};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::{json, Value};

pub const X_RATELIMIT_LIMIT: HeaderName = HeaderName::from_static("x-ratelimit-limit");

#[derive(Debug)]
pub struct ApiError {
    pub status: StatusCode,
    pub detail: String,
    /// When set, the JSON body also contains `"retry_after": <seconds>`.
    pub body_retry_after: Option<u32>,
    pub retry_after_header: Option<HeaderValue>,
    pub ratelimit_limit: Option<HeaderValue>,
}

impl ApiError {
    pub fn new(status: StatusCode, detail: impl Into<String>) -> Self {
        Self {
            status,
            detail: detail.into(),
            body_retry_after: None,
            retry_after_header: None,
            ratelimit_limit: None,
        }
    }

    /// Client body stays `Internal Server Error`. `reason` is the Sentry message.
    pub fn internal(reason: impl std::fmt::Display) -> Self {
        tracing::error!("{reason}");
        Self::new(StatusCode::INTERNAL_SERVER_ERROR, "Internal Server Error")
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let value: Value = if let Some(seconds) = self.body_retry_after {
            json!({"detail": self.detail, "retry_after": seconds})
        } else {
            json!({"detail": self.detail})
        };
        let body = serde_json::to_vec(&value)
            .unwrap_or_else(|_| br#"{"detail":"Internal Server Error"}"#.to_vec());
        let mut response = Response::new(axum::body::Body::from(body));
        *response.status_mut() = self.status;
        let headers = response.headers_mut();
        headers.insert(
            header::CONTENT_TYPE,
            HeaderValue::from_static("application/json"),
        );
        headers.insert(header::CACHE_CONTROL, HeaderValue::from_static("no-store"));
        if let Some(value) = self.retry_after_header {
            headers.insert(header::RETRY_AFTER, value);
        }
        if let Some(value) = self.ratelimit_limit {
            headers.insert(X_RATELIMIT_LIMIT, value);
        }
        response
    }
}
