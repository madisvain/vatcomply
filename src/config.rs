//! Process configuration. Every documented knob is an environment variable.
//! `today` and the VIES retry base are test hooks and are not read from the environment.

use std::env;
use std::net::IpAddr;
use std::path::PathBuf;
use std::time::Duration;

use crate::date::Date;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LogFormat {
    Json,
    Pretty,
}

#[derive(Clone, Debug)]
pub struct Config {
    pub port: u16,
    pub bind: IpAddr,
    pub data_dir: PathBuf,
    pub rates_refresh_secs: u64,
    pub vies_timeout: Duration,
    pub vies_cache_ttl: Duration,
    pub vies_retry_base: Duration,
    pub rate_limit_rps: u32,
    pub rate_limit_burst: u32,
    pub trusted_ip_header: Option<String>,
    pub geo_country_headers: Vec<String>,
    pub geoip_db_path: Option<PathBuf>,
    pub public_base_url: String,
    pub log_format: LogFormat,
    pub log_level: String,
    pub metrics: bool,
    pub ecb_hist_url: String,
    pub ecb_hist_90d_url: String,
    pub vies_url: String,
    pub today: Option<Date>,
}

impl Config {
    pub fn from_env() -> Result<Self, String> {
        let mut config = Self::defaults();
        config.port = env_parse("PORT", config.port, "a port number")?;
        config.bind = env_parse("BIND", config.bind, "an IP address")?;
        if let Some(value) = env_nonempty("DATA_DIR") {
            config.data_dir = PathBuf::from(value);
        }
        config.rates_refresh_secs = env_parse(
            "RATES_REFRESH_SECS",
            config.rates_refresh_secs,
            "an integer",
        )?;
        let vies_timeout = env_parse("VIES_TIMEOUT_SECS", 10, "an integer")?;
        config.vies_timeout = Duration::from_secs(vies_timeout);
        let cache_ttl = env_parse("VIES_CACHE_TTL_SECS", 300, "an integer")?;
        config.vies_cache_ttl = Duration::from_secs(cache_ttl);
        config.rate_limit_rps = env_parse("RATE_LIMIT_RPS", 0, "an integer")?;
        config.rate_limit_burst = env_parse("RATE_LIMIT_BURST", 4, "an integer")?;
        config.trusted_ip_header = env_nonempty("TRUSTED_IP_HEADER");
        if let Some(value) = env_nonempty("GEO_COUNTRY_HEADERS") {
            config.geo_country_headers = split_headers(&value);
        }
        if let Some(value) = env_nonempty("GEOIP_DB_PATH") {
            config.geoip_db_path = Some(PathBuf::from(value));
        }
        if let Some(value) = env_nonempty("PUBLIC_BASE_URL") {
            config.public_base_url = value.trim_end_matches('/').to_string();
        }
        if let Some(value) = env_nonempty("LOG_FORMAT") {
            config.log_format = match value.as_str() {
                "json" => LogFormat::Json,
                "pretty" => LogFormat::Pretty,
                other => return Err(format!("LOG_FORMAT must be json or pretty, got {other}")),
            };
        }
        if let Some(value) = env_nonempty("LOG_LEVEL") {
            config.log_level = value;
        }
        config.metrics = env_flag("METRICS")?;
        if let Some(value) = env_nonempty("ECB_HIST_URL") {
            config.ecb_hist_url = value;
        }
        if let Some(value) = env_nonempty("ECB_HIST_90D_URL") {
            config.ecb_hist_90d_url = value;
        }
        if let Some(value) = env_nonempty("VIES_URL") {
            config.vies_url = value;
        }
        Ok(config)
    }

    pub fn test_default() -> Self {
        let mut config = Self::defaults();
        config.data_dir = PathBuf::from("/nonexistent/vatcomply-v2-test");
        config.ecb_hist_url = "http://127.0.0.1:1/eurofxref-hist.xml".to_string();
        config.ecb_hist_90d_url = "http://127.0.0.1:1/eurofxref-hist-90d.xml".to_string();
        config.vies_url = "http://127.0.0.1:1/vies".to_string();
        config.vies_timeout = Duration::from_secs(2);
        config.vies_retry_base = Duration::from_millis(0);
        config.today = Date::parse("2026-10-04").ok();
        config
    }

    pub fn today(&self) -> Date {
        self.today.unwrap_or_else(crate::date::utc_today)
    }

    fn defaults() -> Self {
        Self {
            port: 8000,
            bind: IpAddr::from([0, 0, 0, 0]),
            data_dir: PathBuf::from("./data"),
            rates_refresh_secs: 3600,
            vies_timeout: Duration::from_secs(10),
            vies_cache_ttl: Duration::from_secs(300),
            vies_retry_base: Duration::from_millis(400),
            rate_limit_rps: 0,
            rate_limit_burst: 4,
            trusted_ip_header: None,
            geo_country_headers: split_headers("CF-IPCountry,Cdn-RequestCountryCode"),
            geoip_db_path: None,
            public_base_url: "http://localhost:8000".to_string(),
            log_format: LogFormat::Pretty,
            log_level: "info".to_string(),
            metrics: false,
            ecb_hist_url: "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
                .to_string(),
            ecb_hist_90d_url: "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
                .to_string(),
            vies_url: "https://ec.europa.eu/taxation_customs/vies/services/checkVatService"
                .to_string(),
            today: None,
        }
    }
}

pub fn help_text() -> &'static str {
    "\
vatcomply — EU VAT, ECB rates, and geolocation API

USAGE:
    vatcomply [serve]
    vatcomply healthcheck
    vatcomply --help

COMMANDS:
    serve          Start the HTTP server (default when no command is given)
    healthcheck    GET http://127.0.0.1:$PORT/healthz and exit 0 on HTTP 200
    --help, -h     Show this text

ENVIRONMENT:
    PORT                    Listen port (default 8000)
    BIND                    Listen address (default 0.0.0.0)
    DATA_DIR                Snapshot directory (default ./data, Docker /data)
    RATES_REFRESH_SECS      ECB refresh interval (default 3600)
    VIES_TIMEOUT_SECS       Per-attempt VIES timeout (default 10)
    VIES_CACHE_TTL_SECS     Cache TTL for VAT results, valid and invalid (default 300)
    RATE_LIMIT_RPS          Requests per second per client IP (default 0 = off).
                            Production sets 2.
    RATE_LIMIT_BURST        Burst size used with RATE_LIMIT_RPS (default 4)
    TRUSTED_IP_HEADER       Header carrying the client IP. Empty = socket peer.
                            Never reads X-Forwarded-For unless this names it.
                            Production: CF-Connecting-IP
    GEO_COUNTRY_HEADERS     Comma-separated country headers, first hit wins
                            (default CF-IPCountry,Cdn-RequestCountryCode)
    GEOIP_DB_PATH           Optional MaxMind .mmdb used when no country header matches
    PUBLIC_BASE_URL         Absolute origin for links on GET / (default http://localhost:8000)
    LOG_FORMAT              json or pretty (default pretty)
    LOG_LEVEL               tracing filter (default info)
    SENTRY_DSN              Sentry DSN. Empty or unset disables error reporting.
    METRICS                 1 mounts GET /metrics (default 0)
    ECB_HIST_URL            Full ECB history URL (advanced, has a default)
    ECB_HIST_90D_URL        90-day ECB URL (advanced, has a default)
    VIES_URL                VIES SOAP endpoint (advanced, has a default)

/health, /healthz, /ready, /readyz, and /metrics are not rate limited.
"
}

fn env_nonempty(key: &str) -> Option<String> {
    env::var(key)
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

fn env_parse<T: std::str::FromStr>(key: &str, default: T, what: &str) -> Result<T, String> {
    match env_nonempty(key) {
        None => Ok(default),
        Some(value) => value
            .parse()
            .map_err(|_| format!("{key} must be {what}, got {value}")),
    }
}

fn env_flag(key: &str) -> Result<bool, String> {
    match env_nonempty(key) {
        None => Ok(false),
        Some(value) if value == "1" || value.eq_ignore_ascii_case("true") => Ok(true),
        Some(value) if value == "0" || value.eq_ignore_ascii_case("false") => Ok(false),
        Some(value) => Err(format!("{key} must be 0 or 1, got {value}")),
    }
}

fn split_headers(value: &str) -> Vec<String> {
    value
        .split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty())
        .map(str::to_string)
        .collect()
}
