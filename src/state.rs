//! Process state. Rates live in an `ArcSwap` so a refresh never blocks readers.

use std::sync::Arc;

use arc_swap::ArcSwap;
use axum::http::HeaderName;
use bytes::Bytes;

use crate::config::Config;
use crate::data::StaticData;
use crate::geo::GeoDb;
use crate::iban::IbanRegistry;
use crate::rates::book::RateBook;
use crate::rates::snapshot;
use crate::vies::ViesService;

#[derive(Clone)]
pub struct AppState {
    pub config: Config,
    pub rates: Arc<ArcSwap<RateBook>>,
    pub static_data: Arc<StaticData>,
    pub iban: Arc<IbanRegistry>,
    pub vies: Arc<ViesService>,
    pub geo: Option<GeoDb>,
    pub openapi: Bytes,
    pub docs_html: Bytes,
    pub metrics: Option<Arc<Metrics>>,
}

pub struct Metrics {
    pub registry: prometheus::Registry,
    pub requests: prometheus::IntCounterVec,
}

impl AppState {
    pub fn load(config: Config) -> Result<(Self, bool), String> {
        validate_headers(&config)?;
        let loaded = snapshot::load_initial(&config.data_dir)?;
        let disk_valid = loaded.disk_valid;
        let openapi = crate::http::spec_json()?;
        let docs_html = Bytes::from(crate::http::docs_page(&openapi));
        let metrics = if config.metrics {
            Some(Arc::new(build_metrics()?))
        } else {
            None
        };
        let geo = match &config.geoip_db_path {
            Some(path) => Some(GeoDb::open(path)?),
            None => None,
        };
        Ok((
            Self {
                rates: Arc::new(ArcSwap::from_pointee(loaded.book)),
                static_data: Arc::new(StaticData::load()?),
                iban: Arc::new(IbanRegistry::load()?),
                vies: Arc::new(ViesService::new(&config)?),
                geo,
                openapi: Bytes::from(openapi),
                docs_html,
                metrics,
                config,
            },
            disk_valid,
        ))
    }
}

fn validate_headers(config: &Config) -> Result<(), String> {
    for name in &config.geo_country_headers {
        HeaderName::from_bytes(name.as_bytes())
            .map_err(|_| format!("GEO_COUNTRY_HEADERS contains invalid name {name}"))?;
    }
    if let Some(name) = &config.trusted_ip_header {
        HeaderName::from_bytes(name.as_bytes())
            .map_err(|_| format!("TRUSTED_IP_HEADER is not a header name: {name}"))?;
    }
    Ok(())
}

fn build_metrics() -> Result<Metrics, String> {
    let registry = prometheus::Registry::new();
    let requests = prometheus::IntCounterVec::new(
        prometheus::Opts::new("http_requests_total", "HTTP responses by status"),
        &["status"],
    )
    .map_err(|error| error.to_string())?;
    registry
        .register(Box::new(requests.clone()))
        .map_err(|error| error.to_string())?;
    Ok(Metrics { registry, requests })
}
