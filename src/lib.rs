//! VATComply HTTP service.

use std::net::SocketAddr;
use std::time::Duration;

use axum::ServiceExt;
use tokio::net::TcpListener;
use tokio_util::sync::CancellationToken;
use tracing_subscriber::prelude::*;
use tracing_subscriber::EnvFilter;

use crate::config::{help_text, Config, LogFormat};
use crate::http::router;
use crate::state::AppState;

pub mod codes;
pub mod config;
pub mod data;
pub mod date;
pub mod error;
pub mod geo;
pub mod http;
pub mod iban;
pub mod query;
pub mod rates;
pub mod state;
pub mod vies;

pub fn run() -> Result<i32, String> {
    let mut args = std::env::args().skip(1);
    match args.next().as_deref() {
        Some("--help" | "-h" | "help") => {
            print!("{}", help_text());
            Ok(0)
        }
        Some("healthcheck") => healthcheck(),
        Some("serve") | None => {
            let config = Config::from_env()?;
            let _sentry = init_sentry();
            init_tracing(&config)?;
            let runtime = tokio::runtime::Builder::new_multi_thread()
                .enable_all()
                .build()
                .map_err(|error| error.to_string())?;
            runtime.block_on(serve(config))?;
            Ok(0)
        }
        Some(other) => Err(format!("unknown command {other}")),
    }
}

pub async fn serve(config: Config) -> Result<(), String> {
    let (state, disk_valid) = AppState::load(config)?;
    let cancel = CancellationToken::new();
    let refresh_state = state.clone();
    let refresh_cancel = cancel.clone();
    let task = tokio::spawn(async move {
        crate::rates::refresh::run(refresh_state, refresh_cancel, disk_valid).await;
    });
    let addr = SocketAddr::from((state.config.bind, state.config.port));
    let listener = TcpListener::bind(addr)
        .await
        .map_err(|error| format!("bind {addr}: {error}"))?;
    let bound = listener.local_addr().map_err(|error| error.to_string())?;
    tracing::info!(addr = %bound, "listening");
    axum::serve(
        listener,
        router(state.clone()).into_make_service_with_connect_info::<SocketAddr>(),
    )
    .with_graceful_shutdown(shutdown_signal())
    .await
    .map_err(|error| format!("server: {error}"))?;
    cancel.cancel();
    let _ = task.await;
    let book = state.rates.load_full();
    if let Err(error) = crate::rates::snapshot::write_snapshot(&state.config.data_dir, &book) {
        tracing::error!(%error, "snapshot flush on shutdown failed");
    }
    Ok(())
}

async fn shutdown_signal() {
    let ctrl_c = async {
        let _ = tokio::signal::ctrl_c().await;
    };
    #[cfg(unix)]
    let terminate = async {
        if let Ok(mut signal) =
            tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
        {
            signal.recv().await;
        }
    };
    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();
    tokio::select! {
        _ = ctrl_c => {}
        _ = terminate => {}
    }
}

fn healthcheck() -> Result<i32, String> {
    let port = std::env::var("PORT")
        .ok()
        .and_then(|value| value.parse::<u16>().ok())
        .unwrap_or(8000);
    let mut stream = std::net::TcpStream::connect(format!("127.0.0.1:{port}"))
        .map_err(|error| error.to_string())?;
    stream
        .set_read_timeout(Some(Duration::from_secs(2)))
        .map_err(|error| error.to_string())?;
    stream
        .set_write_timeout(Some(Duration::from_secs(2)))
        .map_err(|error| error.to_string())?;
    let request = "GET /healthz HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    std::io::Write::write_all(&mut stream, request.as_bytes())
        .map_err(|error| error.to_string())?;
    let mut buf = [0u8; 256];
    let read = std::io::Read::read(&mut stream, &mut buf).map_err(|error| error.to_string())?;
    let text = String::from_utf8_lossy(&buf[..read]);
    if text.starts_with("HTTP/1.1 200") || text.starts_with("HTTP/1.0 200") {
        Ok(0)
    } else {
        Ok(1)
    }
}

fn init_sentry() -> sentry::ClientInitGuard {
    let mut options = sentry::ClientOptions::new().before_send(scrub_event);
    if std::env::var("SENTRY_RELEASE")
        .ok()
        .is_none_or(|value| value.trim().is_empty())
    {
        options = options.maybe_release(sentry::release_name!());
    }
    sentry::init(options)
}

/// `ERROR` logs become Sentry events. Warnings, including VIES faults, do not.
pub(crate) fn error_tracing_layer<S>() -> sentry::integrations::tracing::SentryLayer<S>
where
    S: tracing::Subscriber + for<'lookup> tracing_subscriber::registry::LookupSpan<'lookup>,
{
    sentry::integrations::tracing::layer()
        .event_filter(|metadata: &tracing::Metadata<'_>| {
            if *metadata.level() == tracing::Level::ERROR {
                sentry::integrations::tracing::EventFilter::Event
            } else {
                sentry::integrations::tracing::EventFilter::Ignore
            }
        })
        .span_filter(|_| false)
}

pub(crate) fn scrub_event(
    mut event: sentry::protocol::Event<'static>,
) -> Option<sentry::protocol::Event<'static>> {
    if let Some(request) = event.request.as_mut() {
        if let Some(url) = request.url.as_mut() {
            if let Some(query) = url.query().map(str::to_owned) {
                let redacted = crate::query::redact(&query);
                url.set_query(Some(&redacted));
            }
        }
        if let Some(query) = request.query_string.as_mut() {
            *query = crate::query::redact(query);
        }
    }
    Some(event)
}

fn init_tracing(config: &Config) -> Result<(), String> {
    let filter =
        EnvFilter::try_new(&config.log_level).map_err(|error| format!("LOG_LEVEL: {error}"))?;
    match config.log_format {
        LogFormat::Json => {
            tracing_subscriber::registry()
                .with(tracing_subscriber::fmt::layer().json().with_filter(filter))
                .with(error_tracing_layer())
                .try_init()
                .ok();
        }
        LogFormat::Pretty => {
            tracing_subscriber::registry()
                .with(tracing_subscriber::fmt::layer().with_filter(filter))
                .with(error_tracing_layer())
                .try_init()
                .ok();
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scrub_redacts_vat_and_iban() {
        let mut event = sentry::protocol::Event::new();
        event.request = Some(sentry::protocol::Request {
            url: Some(
                "https://api.vatcomply.com/vat?vat_number=DE123456789&iban=DE89370400440532013000&base=EUR"
                    .parse()
                    .unwrap(),
            ),
            query_string: Some(
                "vat_number=DE123456789&iban=DE89370400440532013000&base=EUR".to_string(),
            ),
            ..Default::default()
        });
        let event = scrub_event(event).unwrap();
        let request = event.request.unwrap();
        let query = request.url.unwrap().query().unwrap().to_string();
        let query_string = request.query_string.unwrap();
        for value in [&query, &query_string] {
            assert!(!value.contains("DE123456789"), "{value}");
            assert!(!value.contains("DE89370400440532013000"), "{value}");
            assert!(value.contains("vat_number=DE***"), "{value}");
            assert!(value.contains("iban=***"), "{value}");
            assert!(value.contains("base=EUR"), "{value}");
        }
    }
}
