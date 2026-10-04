//! VATComply HTTP service.

use std::net::SocketAddr;
use std::time::Duration;

use axum::ServiceExt;
use tokio::net::TcpListener;
use tokio_util::sync::CancellationToken;
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

fn init_tracing(config: &Config) -> Result<(), String> {
    let filter =
        EnvFilter::try_new(&config.log_level).map_err(|error| format!("LOG_LEVEL: {error}"))?;
    match config.log_format {
        LogFormat::Json => {
            tracing_subscriber::fmt()
                .json()
                .with_env_filter(filter)
                .try_init()
                .ok();
        }
        LogFormat::Pretty => {
            tracing_subscriber::fmt()
                .with_env_filter(filter)
                .try_init()
                .ok();
        }
    }
    Ok(())
}
