//! Embedded countries, currencies, and VAT rates.
//!
//! Unfiltered responses are the captured production bytes. Filters keep those
//! object slices so key order and number text stay intact.

use serde::Deserialize;

use crate::codes;

const COUNTRIES_RAW: &str = include_str!("../data/countries.json");
const CURRENCIES_RAW: &str = include_str!("../data/currencies.json");
const VAT_RATES_RAW: &str = include_str!("../data/vat_rates.json");

pub struct StaticData {
    pub countries_raw: &'static str,
    countries: Vec<CountryRow>,
    pub currencies_raw: &'static str,
    currencies: Vec<CurrencyRow>,
    pub vat_raw: &'static str,
    vat: Vec<VatRow>,
}

struct CountryRow {
    slice: &'static str,
    iso2: String,
    iso3: String,
    name: String,
    region: String,
    subregion: String,
    currency: String,
}

struct CurrencyRow {
    key: String,
    slice: &'static str,
    name: String,
}

struct VatRow {
    slice: &'static str,
    country_code: String,
}

#[derive(Deserialize)]
struct CountryFields {
    iso2: String,
    iso3: String,
    name: String,
    region: String,
    subregion: String,
    currency: String,
}

#[derive(Deserialize)]
struct CurrencyFields {
    name: String,
}

#[derive(Deserialize)]
struct VatFields {
    country_code: String,
}

impl StaticData {
    pub fn load() -> Result<Self, String> {
        let country_slices = split_array_objects(COUNTRIES_RAW)
            .map_err(|error| format!("countries.json: {error}"))?;
        let mut countries = Vec::with_capacity(country_slices.len());
        for slice in country_slices {
            let fields: CountryFields = serde_json::from_str(slice)
                .map_err(|error| format!("countries.json object: {error}"))?;
            countries.push(CountryRow {
                slice,
                iso2: fields.iso2,
                iso3: fields.iso3,
                name: fields.name,
                region: fields.region,
                subregion: fields.subregion,
                currency: fields.currency,
            });
        }
        if !countries.iter().any(|row| row.iso2 == "GR") {
            return Err("countries.json is missing GR".to_string());
        }

        let currency_fields = split_object_entries(CURRENCIES_RAW)
            .map_err(|error| format!("currencies.json: {error}"))?;
        let mut currencies = Vec::with_capacity(currency_fields.len());
        for (key, value) in currency_fields {
            let fields: CurrencyFields = serde_json::from_str(value)
                .map_err(|error| format!("currencies.json {key}: {error}"))?;
            currencies.push(CurrencyRow {
                key,
                slice: value,
                name: fields.name,
            });
        }

        let vat_slices = split_array_objects(VAT_RATES_RAW)
            .map_err(|error| format!("vat_rates.json: {error}"))?;
        let mut vat = Vec::with_capacity(vat_slices.len());
        for slice in vat_slices {
            let fields: VatFields = serde_json::from_str(slice)
                .map_err(|error| format!("vat_rates.json object: {error}"))?;
            vat.push(VatRow {
                slice,
                country_code: fields.country_code,
            });
        }
        for code in codes::EU_VAT_MEMBERS {
            if !vat.iter().any(|row| row.country_code == code) {
                return Err(format!("vat_rates.json is missing {code}"));
            }
        }

        Ok(Self {
            countries_raw: COUNTRIES_RAW,
            countries,
            currencies_raw: CURRENCIES_RAW,
            currencies,
            vat_raw: VAT_RATES_RAW,
            vat,
        })
    }

    pub fn countries(
        &self,
        search: Option<&str>,
        region: Option<&str>,
        subregion: Option<&str>,
        currency: Option<&str>,
    ) -> String {
        if blank(search) && blank(region) && blank(subregion) && blank(currency) {
            return self.countries_raw.to_string();
        }
        let search_l = search.unwrap_or("").to_lowercase();
        let mut slices = Vec::new();
        for row in &self.countries {
            if !blank(search) {
                let name = row.name.to_lowercase();
                let iso2 = row.iso2.to_lowercase();
                let iso3 = row.iso3.to_lowercase();
                if !name.contains(&search_l)
                    && !iso2.contains(&search_l)
                    && !iso3.contains(&search_l)
                {
                    continue;
                }
            }
            if !blank(region) && !eq_ignore(region.unwrap_or(""), &row.region) {
                continue;
            }
            if !blank(subregion) && !eq_ignore(subregion.unwrap_or(""), &row.subregion) {
                continue;
            }
            if !blank(currency) && !eq_ignore(currency.unwrap_or(""), &row.currency) {
                continue;
            }
            slices.push(row.slice);
        }
        join_array(&slices)
    }

    pub fn country_slice(&self, iso2: &str) -> Option<&'static str> {
        self.countries
            .iter()
            .find(|row| row.iso2.eq_ignore_ascii_case(iso2))
            .map(|row| row.slice)
    }

    pub fn currencies(&self, search: Option<&str>) -> String {
        if blank(search) {
            return self.currencies_raw.to_string();
        }
        let term = search.unwrap_or("").to_lowercase();
        let mut body = String::from("{");
        let mut first = true;
        for row in &self.currencies {
            if !row.key.to_lowercase().contains(&term) && !row.name.to_lowercase().contains(&term) {
                continue;
            }
            if !first {
                body.push(',');
            }
            first = false;
            body.push('"');
            body.push_str(&row.key);
            body.push_str("\":");
            body.push_str(row.slice);
        }
        body.push('}');
        body
    }

    pub fn vat_rates(&self, country_code: Option<&str>) -> String {
        if blank(country_code) {
            return self.vat_raw.to_string();
        }
        let wanted = country_code.unwrap_or("");
        let slices: Vec<&str> = self
            .vat
            .iter()
            .filter(|row| row.country_code.eq_ignore_ascii_case(wanted))
            .map(|row| row.slice)
            .collect();
        join_array(&slices)
    }
}

fn blank(value: Option<&str>) -> bool {
    match value {
        None | Some("") => true,
        Some(_) => false,
    }
}

fn eq_ignore(left: &str, right: &str) -> bool {
    left.to_lowercase() == right.to_lowercase()
}

fn join_array(slices: &[&str]) -> String {
    let mut body = String::from("[");
    for (index, slice) in slices.iter().enumerate() {
        if index > 0 {
            body.push(',');
        }
        body.push_str(slice);
    }
    body.push(']');
    body
}

fn split_array_objects(raw: &str) -> Result<Vec<&str>, String> {
    let bytes = raw.as_bytes();
    let mut index = 0;
    skip_ws(bytes, &mut index);
    if index >= bytes.len() || bytes[index] != b'[' {
        return Err("expected an array".to_string());
    }
    index += 1;
    let mut objects = Vec::new();
    loop {
        skip_ws(bytes, &mut index);
        if index >= bytes.len() {
            return Err("unterminated array".to_string());
        }
        if bytes[index] == b']' {
            break;
        }
        if bytes[index] == b',' {
            index += 1;
            continue;
        }
        if bytes[index] != b'{' {
            return Err("expected an object".to_string());
        }
        let start = index;
        index = skip_value(bytes, index)?;
        objects.push(&raw[start..index]);
    }
    Ok(objects)
}

fn split_object_entries(raw: &str) -> Result<Vec<(String, &str)>, String> {
    let bytes = raw.as_bytes();
    let mut index = 0;
    skip_ws(bytes, &mut index);
    if index >= bytes.len() || bytes[index] != b'{' {
        return Err("expected an object".to_string());
    }
    index += 1;
    let mut entries = Vec::new();
    loop {
        skip_ws(bytes, &mut index);
        if index >= bytes.len() {
            return Err("unterminated object".to_string());
        }
        if bytes[index] == b'}' {
            break;
        }
        if bytes[index] == b',' {
            index += 1;
            continue;
        }
        if bytes[index] != b'"' {
            return Err("expected an object key".to_string());
        }
        let key_end = skip_string(bytes, index)?;
        let key = serde_json::from_str::<String>(&raw[index..key_end])
            .map_err(|error| format!("object key: {error}"))?;
        index = key_end;
        skip_ws(bytes, &mut index);
        if index >= bytes.len() || bytes[index] != b':' {
            return Err("expected ':'".to_string());
        }
        index += 1;
        skip_ws(bytes, &mut index);
        let value_start = index;
        index = skip_value(bytes, index)?;
        entries.push((key, &raw[value_start..index]));
    }
    Ok(entries)
}

fn skip_ws(bytes: &[u8], index: &mut usize) {
    while *index < bytes.len() && bytes[*index].is_ascii_whitespace() {
        *index += 1;
    }
}

fn skip_value(bytes: &[u8], mut index: usize) -> Result<usize, String> {
    if index >= bytes.len() {
        return Err("unexpected end of json".to_string());
    }
    match bytes[index] {
        b'{' | b'[' => skip_container(bytes, index),
        b'"' => skip_string(bytes, index),
        _ => {
            while index < bytes.len() && !matches!(bytes[index], b',' | b']' | b'}') {
                index += 1;
            }
            Ok(index)
        }
    }
}

fn skip_container(bytes: &[u8], start: usize) -> Result<usize, String> {
    let mut index = start;
    let mut depth = 0i32;
    let mut in_string = false;
    let mut escape = false;
    while index < bytes.len() {
        let byte = bytes[index];
        if in_string {
            if escape {
                escape = false;
            } else if byte == b'\\' {
                escape = true;
            } else if byte == b'"' {
                in_string = false;
            }
        } else if byte == b'"' {
            in_string = true;
        } else if byte == b'{' || byte == b'[' {
            depth += 1;
        } else if byte == b'}' || byte == b']' {
            depth -= 1;
            if depth == 0 {
                return Ok(index + 1);
            }
        }
        index += 1;
    }
    Err("unterminated json value".to_string())
}

fn skip_string(bytes: &[u8], start: usize) -> Result<usize, String> {
    let mut index = start + 1;
    let mut escape = false;
    while index < bytes.len() {
        let byte = bytes[index];
        if escape {
            escape = false;
        } else if byte == b'\\' {
            escape = true;
        } else if byte == b'"' {
            return Ok(index + 1);
        }
        index += 1;
    }
    Err("unterminated string".to_string())
}

/// Insert `country_code` after `iso3` and `ip` before the closing brace.
#[allow(clippy::result_unit_err)]
pub fn geolocate_body(slice: &str, country_code: &str, ip: Option<&str>) -> Result<String, ()> {
    let marker = "\"iso3\":";
    let marker_at = slice.find(marker).ok_or(())?;
    let mut index = marker_at + marker.len();
    let bytes = slice.as_bytes();
    while index < bytes.len() && bytes[index].is_ascii_whitespace() {
        index += 1;
    }
    if index >= bytes.len() || bytes[index] != b'"' {
        return Err(());
    }
    index = skip_string(bytes, index).map_err(|_| ())?;
    let ip_json = match ip {
        None => "null".to_string(),
        Some(value) => serde_json::to_string(value).map_err(|_| ())?,
    };
    let mut body = String::with_capacity(slice.len() + 48);
    body.push_str(&slice[..index]);
    body.push_str(",\"country_code\":");
    body.push_str(&serde_json::to_string(country_code).map_err(|_| ())?);
    let tail = &slice[index..];
    let trimmed = tail.trim_end();
    let without = trimmed.strip_suffix('}').ok_or(())?;
    body.push_str(without);
    body.push_str(",\"ip\":");
    body.push_str(&ip_json);
    body.push('}');
    Ok(body)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn members_and_slices_match_goldens() {
        let data = StaticData::load().unwrap();
        assert!(data.countries.iter().any(|row| row.iso2 == "GR"));
        assert!(!data.countries.iter().any(|row| row.iso2 == "EL"));
        const EU: [&str; 27] = [
            "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU",
            "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK",
        ];
        assert_eq!(data.vat.len(), EU.len());
        for code in EU {
            assert!(
                data.vat.iter().any(|row| row.country_code == code),
                "missing VAT member {code}"
            );
        }
        let estonia = data.countries(Some("Estonia"), None, None, None);
        let golden = include_str!("../tests/golden/countries_estonia.json");
        let golden: serde_json::Value = serde_json::from_str(golden).unwrap();
        assert_eq!(estonia, golden["body"].as_str().unwrap());
        let usd = data.currencies(Some("usd"));
        let golden = include_str!("../tests/golden/currencies_usd.json");
        let golden: serde_json::Value = serde_json::from_str(golden).unwrap();
        assert_eq!(usd, golden["body"].as_str().unwrap());
        let german = data.vat_rates(Some("de"));
        let golden = include_str!("../tests/golden/vat_rates_de.json");
        let golden: serde_json::Value = serde_json::from_str(golden).unwrap();
        assert_eq!(german, golden["body"].as_str().unwrap());
        assert_eq!(data.vat_rates(Some("GR")), "[]");
        assert_eq!(data.countries(Some("zzzzzzz"), None, None, None), "[]");
        assert!(data.currencies(Some("us")).contains("\"RUB\""));
    }
}
