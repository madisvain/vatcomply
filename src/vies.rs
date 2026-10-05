//! VIES SOAP client: retries, a per-country circuit breaker, and a result cache.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use moka::future::Cache;
use quick_xml::events::Event;
use quick_xml::Reader;
use tokio::sync::Semaphore;

use crate::config::Config;

const TRANSIENT: [&str; 6] = [
    "MS_MAX_CONCURRENT_REQ",
    "MS_MAX_CONCURRENT_REQ_TIME",
    "MS_UNAVAILABLE",
    "SERVICE_UNAVAILABLE",
    "TIMEOUT",
    "GLOBAL_MAX_CONCURRENT_REQ",
];
const ATTEMPTS: u32 = 3;
const BREAKER_THRESHOLD: u32 = 5;
const BREAKER_OPEN: u64 = 30_000;

pub struct ViesService {
    client: reqwest::Client,
    url: String,
    retry_base: Duration,
    cache: Cache<String, VatOk>,
    breakers: Mutex<HashMap<String, CountryBreaker>>,
    semaphore: Semaphore,
    now_ms: Arc<dyn Fn() -> u64 + Send + Sync>,
}

struct CountryBreaker {
    consecutive: u32,
    open_until_ms: u64,
    trial: bool,
}

#[derive(Clone, Debug)]
pub struct VatOk {
    pub valid: bool,
    pub vat_number: String,
    pub country_code: String,
    pub name: Option<String>,
    pub address: String,
}

#[derive(Debug)]
pub enum ViesFailure {
    /// Member-state or transport fault after retries. `detail` is the stable code.
    Unavailable(String),
    /// Client fault such as `INVALID_INPUT`. Not retried and not counted by the breaker.
    BadRequest(String),
    /// Breaker is open. The handler answers `MS_UNAVAILABLE` without calling VIES.
    BreakerOpen,
}

impl ViesService {
    pub fn new(config: &Config) -> Result<Self, String> {
        let client = reqwest::Client::builder()
            .timeout(config.vies_timeout)
            .user_agent("vatcomply/2")
            .build()
            .map_err(|error| format!("VIES client: {error}"))?;
        let cache = Cache::builder()
            .time_to_live(config.vies_cache_ttl)
            .max_capacity(10_000)
            .build();
        Ok(Self {
            client,
            url: config.vies_url.clone(),
            retry_base: config.vies_retry_base,
            cache,
            breakers: Mutex::new(HashMap::new()),
            semaphore: Semaphore::new(4),
            now_ms: Arc::new(unix_millis),
        })
    }

    pub fn with_clock(mut self, now_ms: Arc<dyn Fn() -> u64 + Send + Sync>) -> Self {
        self.now_ms = now_ms;
        self
    }

    pub fn open_breakers(&self) -> std::collections::BTreeMap<String, String> {
        let mut out = std::collections::BTreeMap::new();
        let now = (self.now_ms)();
        let Ok(guard) = self.breakers.lock() else {
            return out;
        };
        for (country, breaker) in guard.iter() {
            if breaker.open_until_ms == 0 {
                continue;
            }
            if now < breaker.open_until_ms {
                out.insert(country.clone(), "open".to_string());
            } else {
                out.insert(country.clone(), "half_open".to_string());
            }
        }
        out
    }

    pub async fn check(&self, vat_number: &str) -> Result<VatOk, ViesFailure> {
        if let Some(hit) = self.cache.get(vat_number).await {
            return Ok(hit);
        }
        let country = vat_number.chars().take(2).collect::<String>();
        if !self.admit(&country) {
            return Err(ViesFailure::BreakerOpen);
        }
        let national = vat_number.get(2..).unwrap_or("");
        let mut last_transient = String::from("TIMEOUT");
        for attempt in 0..ATTEMPTS {
            match self.once(&country, national).await {
                Ok(body) => {
                    self.succeed(&country);
                    // Valid and invalid answers are cached alike: registrations
                    // change rarely, and repeat checks must not reach the
                    // Commission. Faults stay uncached.
                    self.cache
                        .insert(vat_number.to_string(), body.clone())
                        .await;
                    return Ok(body);
                }
                Err(CallError::Permanent(detail)) => {
                    self.note_answered(&country);
                    return Err(ViesFailure::BadRequest(detail));
                }
                Err(CallError::Transient(detail)) => {
                    last_transient = detail;
                    tracing::warn!(
                        country = %country,
                        fault = %last_transient,
                        attempt = attempt + 1,
                        "VIES transient fault"
                    );
                    if attempt + 1 == ATTEMPTS {
                        break;
                    }
                    let delay = self.retry_base.saturating_mul(1 << attempt);
                    if !delay.is_zero() {
                        tokio::time::sleep(delay).await;
                    }
                }
            }
        }
        self.fail_transient(&country);
        tracing::warn!(country = %country, fault = %last_transient, "VIES unavailable");
        Err(ViesFailure::Unavailable(last_transient))
    }

    async fn once(&self, country: &str, national: &str) -> Result<VatOk, CallError> {
        let permit = self
            .semaphore
            .acquire()
            .await
            .map_err(|_| CallError::Transient("TIMEOUT".to_string()))?;
        let envelope = soap_envelope(country, national);
        let response = self
            .client
            .post(&self.url)
            .header("Content-Type", "text/xml; charset=utf-8")
            .header("SOAPAction", "\"\"")
            .body(envelope)
            .send()
            .await;
        drop(permit);
        let response = response.map_err(|_| CallError::Transient("TIMEOUT".to_string()))?;
        let status = response.status();
        if status.as_u16() != 200 && status.as_u16() != 500 {
            return Err(CallError::Transient("TIMEOUT".to_string()));
        }
        let bytes = response
            .bytes()
            .await
            .map_err(|_| CallError::Transient("TIMEOUT".to_string()))?;
        match parse_soap(&bytes) {
            ViesBody::Ok(body) => Ok(body),
            ViesBody::Fault(detail) => {
                if TRANSIENT.iter().any(|code| *code == detail) {
                    Err(CallError::Transient(detail))
                } else {
                    tracing::info!(country = %country, fault = %detail, "VIES fault");
                    Err(CallError::Permanent(detail))
                }
            }
            ViesBody::Unparsed => Err(CallError::Transient("TIMEOUT".to_string())),
        }
    }

    fn admit(&self, country: &str) -> bool {
        let now = (self.now_ms)();
        let Ok(mut guard) = self.breakers.lock() else {
            return false;
        };
        let breaker = guard.entry(country.to_string()).or_insert(CountryBreaker {
            consecutive: 0,
            open_until_ms: 0,
            trial: false,
        });
        if breaker.open_until_ms == 0 {
            return true;
        }
        if now < breaker.open_until_ms {
            return false;
        }
        if breaker.trial {
            return false;
        }
        breaker.trial = true;
        true
    }

    fn succeed(&self, country: &str) {
        if let Ok(mut guard) = self.breakers.lock() {
            guard.remove(country);
        }
    }

    /// A client fault proves the member state answered. It does not increment
    /// the breaker. A half-open probe that gets one closes the breaker.
    fn note_answered(&self, country: &str) {
        let Ok(mut guard) = self.breakers.lock() else {
            return;
        };
        if guard.get(country).is_some_and(|breaker| breaker.trial) {
            guard.remove(country);
        }
    }

    fn fail_transient(&self, country: &str) {
        let now = (self.now_ms)();
        let Ok(mut guard) = self.breakers.lock() else {
            return;
        };
        let breaker = guard.entry(country.to_string()).or_insert(CountryBreaker {
            consecutive: 0,
            open_until_ms: 0,
            trial: false,
        });
        let half_open = breaker.open_until_ms != 0 && now >= breaker.open_until_ms;
        if half_open {
            breaker.consecutive = BREAKER_THRESHOLD;
            breaker.open_until_ms = now.saturating_add(BREAKER_OPEN);
            breaker.trial = false;
            return;
        }
        breaker.consecutive = breaker.consecutive.saturating_add(1);
        breaker.trial = false;
        if breaker.consecutive >= BREAKER_THRESHOLD {
            breaker.open_until_ms = now.saturating_add(BREAKER_OPEN);
        }
    }
}

enum CallError {
    Transient(String),
    Permanent(String),
}

enum ViesBody {
    Ok(VatOk),
    Fault(String),
    Unparsed,
}

fn soap_envelope(country: &str, national: &str) -> String {
    format!(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\
<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\
<soap:Body>\
<checkVat xmlns=\"urn:ec.europa.eu:taxud:vies:services:checkVat:types\">\
<countryCode>{}</countryCode>\
<vatNumber>{}</vatNumber>\
</checkVat>\
</soap:Body>\
</soap:Envelope>",
        xml_escape(country),
        xml_escape(national)
    )
}

fn xml_escape(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

fn note_element(
    element: &quick_xml::events::BytesStart<'_>,
    empty: bool,
    current: &mut String,
    saw_response: &mut bool,
    saw_fault: &mut bool,
    name_nil: &mut bool,
    name: &mut Option<String>,
) {
    *current = local_name(element.name().as_ref());
    if current == "checkVatResponse" {
        *saw_response = true;
    }
    if current == "Fault" {
        *saw_fault = true;
    }
    if current == "name" {
        *name_nil = element.attributes().any(|attribute| {
            attribute
                .ok()
                .map(|attribute| {
                    let key = attribute.key.as_ref();
                    (key == b"nil" || key.ends_with(b":nil"))
                        && (attribute.value.as_ref() == b"true" || attribute.value.as_ref() == b"1")
                })
                .unwrap_or(false)
        });
        if *name_nil {
            *name = None;
        }
    }
    if empty {
        current.clear();
    }
}

fn parse_soap(input: &[u8]) -> ViesBody {
    let mut reader = Reader::from_reader(input);
    reader.config_mut().trim_text(true);
    let mut buf = Vec::new();
    let mut current = String::new();
    let mut name_nil = false;
    let mut saw_response = false;
    let mut saw_fault = false;
    let mut fault = String::new();
    let mut country = String::new();
    let mut number = String::new();
    let mut valid = false;
    let mut saw_valid = false;
    let mut name: Option<String> = None;
    let mut address = String::new();
    let mut saw_address = false;
    loop {
        let event = match reader.read_event_into(&mut buf) {
            Ok(event) => event,
            Err(_) => return ViesBody::Unparsed,
        };
        match event {
            Event::Start(element) => {
                note_element(
                    &element,
                    false,
                    &mut current,
                    &mut saw_response,
                    &mut saw_fault,
                    &mut name_nil,
                    &mut name,
                );
            }
            Event::Empty(element) => {
                note_element(
                    &element,
                    true,
                    &mut current,
                    &mut saw_response,
                    &mut saw_fault,
                    &mut name_nil,
                    &mut name,
                );
            }
            Event::Text(text) => {
                let Ok(decoded) = text.decode() else {
                    return ViesBody::Unparsed;
                };
                let Ok(value) = quick_xml::escape::unescape(decoded.as_ref()) else {
                    return ViesBody::Unparsed;
                };
                match current.as_str() {
                    "faultstring" => fault = value.trim().to_string(),
                    "countryCode" => country = value.to_string(),
                    "vatNumber" => number = value.to_string(),
                    "valid" => {
                        saw_valid = true;
                        valid = value.eq_ignore_ascii_case("true");
                    }
                    "name" if !name_nil => name = Some(value.to_string()),
                    "address" => {
                        saw_address = true;
                        address = value.to_string();
                    }
                    _ => {}
                }
            }
            Event::End(_) => current.clear(),
            Event::Eof => break,
            _ => {}
        }
        buf.clear();
    }
    if saw_fault && !fault.is_empty() {
        return ViesBody::Fault(fault);
    }
    if saw_response && saw_valid {
        return ViesBody::Ok(VatOk {
            valid,
            vat_number: number,
            country_code: country,
            name,
            address: if saw_address {
                address.trim().to_string()
            } else {
                String::new()
            },
        });
    }
    ViesBody::Unparsed
}

fn local_name(name: &[u8]) -> String {
    let text = String::from_utf8_lossy(name);
    text.rsplit(':').next().unwrap_or("").to_string()
}

pub fn vat_json(body: &VatOk) -> String {
    let name = match &body.name {
        None => "null".to_string(),
        Some(value) => serde_json::to_string(value).unwrap_or_else(|_| "null".to_string()),
    };
    format!(
        "{{\"valid\":{},\"vat_number\":{},\"country_code\":{},\"name\":{},\"address\":{}}}",
        if body.valid { "true" } else { "false" },
        serde_json::to_string(&body.vat_number).unwrap_or_else(|_| "\"\"".to_string()),
        serde_json::to_string(&body.country_code).unwrap_or_else(|_| "\"\"".to_string()),
        name,
        serde_json::to_string(&body.address).unwrap_or_else(|_| "\"\"".to_string()),
    )
}

/// Run the SOAP parser and discard the result. Fuzzing calls this.
pub fn parse_vies_response(input: &[u8]) {
    let _ = parse_soap(input);
}

pub fn valid_vat_format(value: &str) -> bool {
    let bytes = value.as_bytes();
    (10..=14).contains(&bytes.len())
        && bytes[0].is_ascii_uppercase()
        && bytes[1].is_ascii_uppercase()
        && bytes[2..]
            .iter()
            .all(|byte| byte.is_ascii_uppercase() || byte.is_ascii_digit())
}

fn unix_millis() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis() as u64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    #[test]
    fn parses_success_nil_and_faults() {
        let ok = parse_soap(include_bytes!(
            "../tests/fixtures/vies/synthetic_valid_true.xml"
        ));
        match ok {
            ViesBody::Ok(body) => {
                assert!(body.valid);
                assert_eq!(body.name.as_deref(), Some("John Doe"));
                assert_eq!(body.address, "123 Main St");
            }
            _ => panic!("expected ok"),
        }
        let nil = parse_soap(include_bytes!(
            "../tests/fixtures/vies/synthetic_name_nil.xml"
        ));
        match nil {
            ViesBody::Ok(body) => assert!(body.name.is_none()),
            _ => panic!("expected nil name"),
        }
        let fault = parse_soap(include_bytes!(
            "../tests/fixtures/vies/synthetic_fault_INVALID_INPUT.xml"
        ));
        match fault {
            ViesBody::Fault(detail) => assert_eq!(detail, "INVALID_INPUT"),
            _ => panic!("expected fault"),
        }
        let timeout = parse_soap(include_bytes!(
            "../tests/fixtures/vies/synthetic_fault_TIMEOUT.xml"
        ));
        match timeout {
            ViesBody::Fault(detail) => assert_eq!(detail, "TIMEOUT"),
            _ => panic!("expected timeout"),
        }
    }

    #[test]
    fn format_pattern() {
        assert!(valid_vat_format("DE123456789"));
        assert!(valid_vat_format("XX12345678"));
        assert!(!valid_vat_format("de123456789"));
        assert!(!valid_vat_format(""));
        assert!(!valid_vat_format("DE123"));
    }

    proptest! {
        #[test]
        fn accepts_the_production_shape(body in "[A-Z0-9]{8,12}") {
            let value = format!("DE{body}");
            prop_assert!(valid_vat_format(&value));
        }

        #[test]
        fn rejects_lowercase_prefix(body in "[0-9A-Z]{8,12}") {
            let value = format!("de{body}");
            prop_assert!(!valid_vat_format(&value));
        }
    }
}
