//! IBAN checks that follow schwifty 2026.3.0.
//!
//! The registry in `data/iban_registry.json` is exported from that release
//! and drives the country checks, field extraction, and the bank catalog
//! (bank names and BICs). Structure and checksum validation are delegated to
//! `iban_validation_rs`, which embeds the official SWIFT IBAN registry plus
//! the same non-registry countries schwifty carries. The JSON `iban` field
//! is the raw query. Error text uses the cleaned string.

use std::collections::BTreeMap;

use iban_validation_rs::{CountrySet, Iban, ValidationError};
use serde::Deserialize;

use crate::error::ApiError;
use axum::http::StatusCode;

const REGISTRY_JSON: &str = include_str!("../data/iban_registry.json");

#[derive(Deserialize)]
struct RawRegistry {
    countries: BTreeMap<String, RawCountry>,
    banks: BTreeMap<String, BTreeMap<String, (String, String)>>,
}

#[derive(Deserialize)]
struct RawCountry {
    name: String,
    in_sepa_zone: bool,
    iban_length: usize,
    bban_spec: String,
    positions: BTreeMap<String, (usize, usize)>,
    bic_lookup: Vec<String>,
}

struct CountrySpec {
    name: String,
    in_sepa_zone: bool,
    iban_length: usize,
    bban_spec: String,
    positions: BTreeMap<String, (usize, usize)>,
    bic_lookup: Vec<String>,
}

pub struct IbanRegistry {
    countries: BTreeMap<String, CountrySpec>,
    banks: BTreeMap<String, BTreeMap<String, (String, String)>>,
}

impl IbanRegistry {
    pub fn load() -> Result<Self, String> {
        let raw: RawRegistry = serde_json::from_str(REGISTRY_JSON)
            .map_err(|error| format!("iban registry: {error}"))?;
        let mut countries = BTreeMap::new();
        for (code, country) in raw.countries {
            countries.insert(
                code,
                CountrySpec {
                    name: country.name,
                    in_sepa_zone: country.in_sepa_zone,
                    iban_length: country.iban_length,
                    bban_spec: country.bban_spec,
                    positions: country.positions,
                    bic_lookup: country.bic_lookup,
                },
            );
        }
        if !countries.contains_key("DE") || !countries.contains_key("GB") {
            return Err("iban registry is missing DE or GB".to_string());
        }
        Ok(Self {
            countries,
            banks: raw.banks,
        })
    }

    pub fn answer(&self, raw_iban: &str) -> Result<String, ApiError> {
        let cleaned = clean(raw_iban);
        if !character_prefix(&cleaned) {
            return Err(bad(format!("Invalid characters in IBAN {cleaned}")));
        }
        let country = &cleaned[..2];
        let Some(spec) = self.countries.get(country) else {
            return Err(bad(format!("Unknown country-code '{country}'")));
        };
        if spec.iban_length != cleaned.len() {
            return Err(bad("Invalid IBAN length"));
        }
        if let Err(error) = Iban::new_with(&cleaned, CountrySet::WithNonRegistry) {
            return Err(map_error(&cleaned, &spec.bban_spec, error));
        }
        let checksum = &cleaned[2..4];
        let bban = &cleaned[4..];
        let bank_code = component(bban, &spec.positions, "bank_code");
        let branch_code = component(bban, &spec.positions, "branch_code");
        let account = component(bban, &spec.positions, "account_code");
        let mut lookup = String::new();
        for name in &spec.bic_lookup {
            lookup.push_str(component(bban, &spec.positions, name));
        }
        let (bank_name, bic) = self
            .banks
            .get(country)
            .and_then(|banks| banks.get(&lookup))
            .map(|(name, bic)| (name.as_str(), bic.as_str()))
            .unwrap_or(("", ""));
        Ok(format!(
            "{{\"valid\":true,\"iban\":{},\"bank_name\":{},\"bic\":{},\"country_code\":{},\"country_name\":{},\"checksum_digits\":{},\"bank_code\":{},\"branch_code\":{},\"account_number\":{},\"bban\":{},\"in_sepa_zone\":{}}}",
            json_string(raw_iban),
            json_string(bank_name),
            json_string(bic),
            json_string(country),
            json_string(&spec.name),
            json_string(checksum),
            json_string(bank_code),
            json_string(branch_code),
            json_string(account),
            json_string(bban),
            if spec.in_sepa_zone { "true" } else { "false" },
        ))
    }
}

fn bad(detail: impl Into<String>) -> ApiError {
    ApiError::new(StatusCode::BAD_REQUEST, detail)
}

/// The crate reports structure and checksum faults in its own terms; the texts
/// stay the schwifty ones so responses do not change.
fn map_error(cleaned: &str, bban_spec: &str, error: ValidationError) -> ApiError {
    let detail = match error {
        ValidationError::StructureIncorrectForCountry => format!(
            "Invalid BBAN structure: '{}' doesn't match '{bban_spec}'",
            &cleaned[4..]
        ),
        ValidationError::ModuloIncorrect | ValidationError::InvalidChecksum => {
            "Invalid checksum digits".to_string()
        }
        ValidationError::InvalidSizeForCountry | ValidationError::TooShort(_) => {
            "Invalid IBAN length".to_string()
        }
        ValidationError::MissingCountry | ValidationError::InvalidCountry => {
            format!("Unknown country-code '{}'", &cleaned[..2])
        }
    };
    bad(detail)
}

fn json_string(value: &str) -> String {
    serde_json::to_string(value).unwrap_or_else(|_| "\"\"".to_string())
}

fn clean(input: &str) -> String {
    input
        .chars()
        .filter(|char| !char.is_whitespace())
        .flat_map(char::to_uppercase)
        .collect()
}

/// `re.match(r"[A-Z]{2}\d{2}[A-Z]*")` only constrains the prefix.
fn character_prefix(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() >= 4
        && bytes[0].is_ascii_uppercase()
        && bytes[1].is_ascii_uppercase()
        && bytes[2].is_ascii_digit()
        && bytes[3].is_ascii_digit()
}

fn component<'a>(
    bban: &'a str,
    positions: &BTreeMap<String, (usize, usize)>,
    name: &str,
) -> &'a str {
    let Some(&(start, end)) = positions.get(name) else {
        return "";
    };
    if start <= end && end <= bban.len() && start <= bban.len() {
        &bban[start..end]
    } else {
        ""
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn registry() -> IbanRegistry {
        IbanRegistry::load().unwrap()
    }

    #[test]
    fn german_and_errors() {
        let registry = registry();
        let body = registry.answer("DE89370400440532013000").unwrap();
        assert!(body.contains("\"bank_name\":\"Commerzbank\""));
        assert!(body.contains("\"bic\":\"COBADEFFXXX\""));
        assert!(body.contains("\"account_number\":\"0532013000\""));
        let lower = registry.answer("de89370400440532013000").unwrap();
        assert!(lower.contains("\"iban\":\"de89370400440532013000\""));
        assert!(lower.contains("\"bank_code\":\"37040044\""));
        let error = registry.answer("").unwrap_err();
        assert_eq!(error.detail, "Invalid characters in IBAN ");
        let error = registry.answer("123").unwrap_err();
        assert_eq!(error.detail, "Invalid characters in IBAN 123");
        let error = registry.answer("DE89370400440532013001").unwrap_err();
        assert_eq!(error.detail, "Invalid checksum digits");
        let error = registry.answer("XX89370400440532013000").unwrap_err();
        assert_eq!(error.detail, "Unknown country-code 'XX'");
        let error = registry.answer("DE8937040044053201300").unwrap_err();
        assert_eq!(error.detail, "Invalid IBAN length");
        let gb = registry.answer("GB82WEST12345698765432").unwrap();
        assert!(gb.contains("\"bank_name\":\"\""));
        assert!(gb.contains("\"branch_code\":\"123456\""));
        assert!(gb.contains("\"country_name\":\"United Kingdom\""));
    }

    #[test]
    fn structure_error_keeps_the_schwifty_text() {
        let registry = registry();
        let error = registry.answer("DE8937040044053201300X").unwrap_err();
        assert_eq!(
            error.detail,
            "Invalid BBAN structure: '37040044053201300X' doesn't match '8!n10!n'"
        );
    }

    #[test]
    fn extraction_matches_the_registry_positions() {
        let registry = registry();
        let fr = registry.answer("FR1420041010050500013M02606").unwrap();
        assert!(fr.contains("\"bank_name\":\"LA BANQUE POSTALE\""));
        assert!(fr.contains("\"bic\":\"PSSTFRPP\""));
        assert!(fr.contains("\"branch_code\":\"01005\""));
        assert!(fr.contains("\"account_number\":\"0500013M026\""));
        let no = registry.answer("NO9386011117947").unwrap();
        assert!(no.contains("\"bank_name\":\"Danske Bank\""));
        assert!(no.contains("\"bic\":\"DABANO22\""));
        assert!(no.contains("\"account_number\":\"111794\""));
    }
}
