//! IBAN checks that follow schwifty 2026.3.0.
//!
//! The registry in `data/iban_registry.json` is exported from that release.
//! `validate_bban` stays off, so national checksums are not checked.
//! The JSON `iban` field is the raw query. Error text uses the cleaned string.

use std::collections::BTreeMap;

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
    tokens: Vec<BbanToken>,
    positions: BTreeMap<String, (usize, usize)>,
    bic_lookup: Vec<String>,
}

struct BbanToken {
    count: usize,
    class: CharClass,
}

enum CharClass {
    Digit,
    Upper,
    AlphaNum,
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
            let tokens = parse_spec(&country.bban_spec)
                .map_err(|error| format!("iban spec {code}: {error}"))?;
            countries.insert(
                code,
                CountrySpec {
                    name: country.name,
                    in_sepa_zone: country.in_sepa_zone,
                    iban_length: country.iban_length,
                    bban_spec: country.bban_spec,
                    tokens,
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
        let bban = &cleaned[4..];
        if !spec_matches(&spec.tokens, bban.as_bytes()) {
            return Err(bad(format!(
                "Invalid BBAN structure: '{bban}' doesn't match '{}'",
                spec.bban_spec
            )));
        }
        let checksum = &cleaned[2..4];
        if !checksum_ok(bban, country, checksum) {
            return Err(bad("Invalid checksum digits"));
        }
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

fn checksum_ok(bban: &str, country: &str, checksum: &str) -> bool {
    let mut rearranged = String::with_capacity(bban.len() + 4);
    rearranged.push_str(bban);
    rearranged.push_str(country);
    rearranged.push_str(checksum);
    mod97(&numerify(&rearranged)) == 1
}

fn numerify(value: &str) -> String {
    let mut out = String::with_capacity(value.len() * 2);
    for char in value.chars() {
        let digit = match char {
            '0'..='9' => (char as u8 - b'0') as u32,
            'A'..='Z' => (char as u8 - b'A') as u32 + 10,
            _ => return String::new(),
        };
        out.push_str(&digit.to_string());
    }
    out
}

fn mod97(digits: &str) -> u32 {
    let mut acc: u32 = 0;
    for byte in digits.bytes() {
        if !byte.is_ascii_digit() {
            return 0;
        }
        acc = (acc * 10 + (byte - b'0') as u32) % 97;
    }
    acc
}

fn parse_spec(spec: &str) -> Result<Vec<BbanToken>, String> {
    let bytes = spec.as_bytes();
    let mut index = 0;
    let mut tokens = Vec::new();
    while index < bytes.len() {
        let start = index;
        while index < bytes.len() && bytes[index].is_ascii_digit() {
            index += 1;
        }
        if start == index {
            return Err(format!("bad spec {spec}"));
        }
        let count: usize = spec[start..index]
            .parse()
            .map_err(|_| format!("bad spec count {spec}"))?;
        if index >= bytes.len() || bytes[index] != b'!' {
            return Err(format!("bad spec {spec}"));
        }
        index += 1;
        if index >= bytes.len() {
            return Err(format!("bad spec {spec}"));
        }
        let class = match bytes[index] {
            b'n' => CharClass::Digit,
            b'a' => CharClass::Upper,
            b'c' => CharClass::AlphaNum,
            _ => return Err(format!("bad spec class in {spec}")),
        };
        index += 1;
        tokens.push(BbanToken { count, class });
    }
    if tokens.is_empty() {
        return Err(format!("empty spec {spec}"));
    }
    Ok(tokens)
}

fn spec_matches(tokens: &[BbanToken], bban: &[u8]) -> bool {
    let mut pos: usize = 0;
    for token in tokens {
        let Some(end) = pos.checked_add(token.count) else {
            return false;
        };
        if end > bban.len() || !class_span(&token.class, &bban[pos..end]) {
            return false;
        }
        pos = end;
    }
    pos == bban.len()
}

fn class_span(class: &CharClass, bytes: &[u8]) -> bool {
    bytes.iter().all(|byte| class_ok(class, *byte))
}

fn class_ok(class: &CharClass, byte: u8) -> bool {
    match class {
        CharClass::Digit => byte.is_ascii_digit(),
        CharClass::Upper => byte.is_ascii_uppercase(),
        CharClass::AlphaNum => byte.is_ascii_digit() || byte.is_ascii_alphabetic(),
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
}
