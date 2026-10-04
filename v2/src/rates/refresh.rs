//! Hourly ECB refresh. The first tick runs at startup.
//!
//! A cold start with no valid disk snapshot fetches the full history. Later
//! ticks, and a start that already has a valid disk snapshot, fetch the 90-day
//! feed and overwrite dates that the feed contains.

use std::sync::atomic::Ordering;
use std::time::Duration;

use tokio::time::{interval, MissedTickBehavior};
use tokio_util::sync::CancellationToken;

use crate::date::{format_unix, unix_now};
use crate::rates::book::RateSource;
use crate::rates::parse::parse_ecb_xml;
use crate::rates::snapshot;
use crate::state::AppState;

const ATTEMPT_TIMEOUT: Duration = Duration::from_secs(60);
const ATTEMPTS: u32 = 3;

pub async fn run(state: AppState, cancel: CancellationToken) {
    let mut prefer_90d = state.disk_valid.load(Ordering::Relaxed);
    let secs = state.config.rates_refresh_secs.max(1);
    let mut ticker = interval(Duration::from_secs(secs));
    ticker.set_missed_tick_behavior(MissedTickBehavior::Skip);
    loop {
        tokio::select! {
            _ = cancel.cancelled() => break,
            _ = ticker.tick() => {}
        }
        if cancel.is_cancelled() {
            break;
        }
        let url = if prefer_90d {
            state.config.ecb_hist_90d_url.clone()
        } else {
            state.config.ecb_hist_url.clone()
        };
        match fetch_with_retry(&url, &cancel).await {
            Ok(xml) => match parse_ecb_xml(&xml) {
                Ok(rows) if !rows.is_empty() => {
                    let current = state.rates.load_full();
                    let mut next = (*current).clone();
                    next.source = RateSource::Ecb;
                    next.fetched_at = format_unix(unix_now());
                    if let Err(error) = next.merge(rows) {
                        tracing::error!(error = %error, "ECB merge failed");
                        continue;
                    }
                    if let Err(error) = snapshot::write_snapshot(&state.config.data_dir, &next) {
                        tracing::error!(error = %error, "failed to write rates snapshot");
                    }
                    let date = next
                        .latest_date()
                        .map(|day| day.to_string())
                        .unwrap_or_default();
                    state.rates.store(std::sync::Arc::new(next));
                    prefer_90d = true;
                    tracing::info!(%date, "ECB rates refreshed");
                }
                Ok(_) => tracing::error!("ECB feed contained no rates"),
                Err(error) => tracing::error!(error = %error.message, "ECB XML parse failed"),
            },
            Err(error) => {
                if cancel.is_cancelled() || error == "cancelled" {
                    break;
                }
                tracing::error!(error = %error, %url, "ECB refresh failed");
            }
        }
    }
}

async fn fetch_with_retry(url: &str, cancel: &CancellationToken) -> Result<Vec<u8>, String> {
    let client = reqwest::Client::builder()
        .timeout(ATTEMPT_TIMEOUT)
        .user_agent("vatcomply/2")
        .build()
        .map_err(|error| error.to_string())?;
    let mut last = String::from("ECB fetch failed");
    for attempt in 1..=ATTEMPTS {
        if cancel.is_cancelled() {
            return Err("cancelled".to_string());
        }
        match fetch_once(&client, url, cancel).await {
            Ok(body) => return Ok(body),
            Err(error) => {
                last = error;
                if attempt == ATTEMPTS || cancel.is_cancelled() {
                    break;
                }
                let delay = Duration::from_millis(500 * 2u64.pow(attempt - 1));
                tokio::select! {
                    _ = cancel.cancelled() => return Err("cancelled".to_string()),
                    _ = tokio::time::sleep(delay) => {}
                }
            }
        }
    }
    Err(last)
}

async fn fetch_once(
    client: &reqwest::Client,
    url: &str,
    cancel: &CancellationToken,
) -> Result<Vec<u8>, String> {
    let request = client.get(url).send();
    let response = tokio::select! {
        _ = cancel.cancelled() => return Err("cancelled".to_string()),
        result = request => result.map_err(|error| error.to_string())?,
    };
    if !response.status().is_success() {
        return Err(format!("ECB status {}", response.status()));
    }
    let body = response.bytes();
    tokio::select! {
        _ = cancel.cancelled() => Err("cancelled".to_string()),
        result = body => result.map(|bytes| bytes.to_vec()).map_err(|error| error.to_string()),
    }
}
