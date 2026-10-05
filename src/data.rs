//! Countries, currencies, and VAT rates.
//!
//! Countries are built at startup from `my_country`, `iso-rs`, and the IANA
//! `tld` set. Currencies are built from `iso_currency` for the ECB code list.
//! VAT rates stay the captured production bytes.
//! Filters keep object slices so key order stays intact.

use my_country::Country;
use serde::{Deserialize, Serialize};
use serde_json::value::RawValue;
use strum::IntoEnumIterator;

use crate::codes;

const VAT_RATES_RAW: &str = include_str!("../data/vat_rates.json");

pub struct StaticData {
    countries_body: String,
    countries: Vec<CountryRow>,
    currencies_body: String,
    currencies: Vec<CurrencyRow>,
    pub vat_raw: &'static str,
    vat: Vec<VatRow>,
}

struct CountryRow {
    slice: String,
    iso2: String,
    iso3: String,
    name: String,
    region: String,
    subregion: String,
    currency: String,
}

struct CurrencyRow {
    key: String,
    slice: String,
    name: String,
}

struct VatRow {
    slice: &'static str,
    country_code: String,
}

#[derive(Deserialize)]
struct VatFields {
    country_code: String,
}

impl StaticData {
    pub fn load() -> Result<Self, String> {
        let mut listed: Vec<Country> = Country::iter().collect();
        listed.sort_by_key(|country| country.alpha2());
        let mut countries = Vec::with_capacity(listed.len());
        for country in listed {
            let iso2 = country.alpha2();
            let iso3 = country.alpha3();
            let name = country.iso_short_name();
            let region = country.region().unwrap_or("");
            let subregion = country.subregion().unwrap_or("");
            let currency = currency_alpha(country.currency_code())?;
            let tld = tld_for(iso2);
            let geo = country.geo();
            let latitude = serde_json::to_value(geo.latitude)
                .map_err(|error| format!("country json: {error}"))?;
            let longitude = serde_json::to_value(geo.longitude)
                .map_err(|error| format!("country json: {error}"))?;
            let slice = serde_json::to_string(&CountryObject {
                iso2,
                iso3,
                name,
                numeric_code: country.numeric_code(),
                phone_code: country.country_code(),
                capital: capital_for(iso2),
                currency: &currency,
                tld: &tld,
                region,
                subregion,
                latitude,
                longitude,
                emoji: country.emoji_flag(),
            })
            .map_err(|error| format!("country json: {error}"))?;
            countries.push(CountryRow {
                slice,
                iso2: iso2.to_string(),
                iso3: iso3.to_string(),
                name: name.to_string(),
                region: region.to_string(),
                subregion: subregion.to_string(),
                currency,
            });
        }
        if !countries.iter().any(|row| row.iso2 == "GR") {
            return Err("country list is missing GR".to_string());
        }
        let countries_body = join_array(
            &countries
                .iter()
                .map(|row| row.slice.as_str())
                .collect::<Vec<_>>(),
        );

        let currencies = currency_rows()?;
        let currencies_body = join_object(&currencies);

        let vat_slices: Vec<&RawValue> = serde_json::from_str(VAT_RATES_RAW)
            .map_err(|error| format!("vat_rates.json: {error}"))?;
        let mut vat = Vec::with_capacity(vat_slices.len());
        for raw in vat_slices {
            let fields: VatFields = serde_json::from_str(raw.get())
                .map_err(|error| format!("vat_rates.json object: {error}"))?;
            vat.push(VatRow {
                slice: static_slice(VAT_RATES_RAW, raw)?,
                country_code: fields.country_code,
            });
        }
        for code in codes::EU_VAT_MEMBERS {
            if !vat.iter().any(|row| row.country_code == code) {
                return Err(format!("vat_rates.json is missing {code}"));
            }
        }

        Ok(Self {
            countries_body,
            countries,
            currencies_body,
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
            return self.countries_body.clone();
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
            slices.push(row.slice.as_str());
        }
        join_array(&slices)
    }

    pub fn country_slice(&self, iso2: &str) -> Option<&str> {
        self.countries
            .iter()
            .find(|row| row.iso2.eq_ignore_ascii_case(iso2))
            .map(|row| row.slice.as_str())
    }

    pub fn currencies(&self, search: Option<&str>) -> String {
        if blank(search) {
            return self.currencies_body.clone();
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
            body.push_str(&row.slice);
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

/// ISO 4217 alphabetic code. `Currency` exposes that code as its variant name.
fn currency_alpha(currency: my_country::Currency) -> Result<String, String> {
    let code = format!("{currency:?}");
    if code.len() == 3 && code.bytes().all(|byte| byte.is_ascii_uppercase()) {
        Ok(code)
    } else {
        Err(format!(
            "currency variant {code} is not an alphabetic ISO 4217 code"
        ))
    }
}

fn capital_for(iso2: &str) -> &str {
    iso_rs::Country::from_alpha_2(iso2)
        .and_then(|rows| rows.first())
        .and_then(|country| country.capital)
        .unwrap_or("")
}

/// Direct hit is `.{iso2}`. `GB` uses `.uk` only when `gb` is absent and `uk` is in the set.
fn tld_for(iso2: &str) -> String {
    let label = iso2.to_ascii_lowercase();
    if tld::exist(&label) {
        return format!(".{label}");
    }
    if iso2 == "GB" && tld::exist("uk") {
        return ".uk".into();
    }
    String::new()
}

#[derive(Serialize)]
struct CountryObject<'a> {
    iso2: &'a str,
    iso3: &'a str,
    name: &'a str,
    numeric_code: u16,
    phone_code: &'a str,
    capital: &'a str,
    currency: &'a str,
    tld: &'a str,
    region: &'a str,
    subregion: &'a str,
    latitude: serde_json::Value,
    longitude: serde_json::Value,
    emoji: &'a str,
}

fn currency_rows() -> Result<Vec<CurrencyRow>, String> {
    let mut rows = Vec::with_capacity(codes::CODES.len());
    for code in codes::CODES {
        let currency = iso_currency::Currency::from_code(code)
            .ok_or_else(|| format!("currency list is missing {code}"))?;
        let decimal_places = currency
            .exponent()
            .ok_or_else(|| format!("currency {code} has no decimal places"))?;
        let numeric_code = format!("{:03}", currency.numeric());
        let currency_symbol = currency.symbol().to_string();
        let countries: Vec<String> = currency.used_by().iter().map(ToString::to_string).collect();
        let name = currency.name();
        let slice = serde_json::to_string(&CurrencyObject {
            name,
            symbol: code,
            numeric_code: &numeric_code,
            currency_symbol: &currency_symbol,
            currency_symbol_narrow: None::<&str>,
            decimal_places,
            rounding: 0,
            countries: &countries,
        })
        .map_err(|error| format!("currency json: {error}"))?;
        rows.push(CurrencyRow {
            key: (*code).to_string(),
            slice,
            name: name.to_string(),
        });
    }
    Ok(rows)
}

#[derive(Serialize)]
struct CurrencyObject<'a> {
    name: &'a str,
    symbol: &'a str,
    numeric_code: &'a str,
    currency_symbol: &'a str,
    currency_symbol_narrow: Option<&'a str>,
    decimal_places: u16,
    rounding: u8,
    countries: &'a [String],
}

fn join_object(rows: &[CurrencyRow]) -> String {
    let mut body = String::from("{");
    for (index, row) in rows.iter().enumerate() {
        if index > 0 {
            body.push(',');
        }
        body.push('"');
        body.push_str(&row.key);
        body.push_str("\":");
        body.push_str(&row.slice);
    }
    body.push('}');
    body
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

/// `RawValue::get` borrows the local reference. The bytes sit inside `base`,
/// which is an `include_str!` buffer, so the subslice is `'static`.
fn static_slice(base: &'static str, raw: &RawValue) -> Result<&'static str, String> {
    let text = raw.get();
    let start = (text.as_ptr() as usize)
        .checked_sub(base.as_ptr() as usize)
        .ok_or_else(|| "raw json value is not inside the embedded document".to_string())?;
    let end = start
        .checked_add(text.len())
        .ok_or_else(|| "raw json value length overflow".to_string())?;
    if end > base.len() {
        return Err("raw json value extends past the embedded document".to_string());
    }
    Ok(&base[start..end])
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

    #[test]
    fn currencies_follow_iso_currency() {
        let data = StaticData::load().unwrap();
        let body = data.currencies(None);
        let mut previous = 0;
        for code in codes::CODES {
            let at = body
                .find(&format!("\"{code}\":"))
                .unwrap_or_else(|| panic!("missing {code}"));
            assert!(at >= previous, "{code} out of order");
            previous = at;
        }
        let value: serde_json::Value = serde_json::from_str(&body).unwrap();
        assert_eq!(value.as_object().unwrap().len(), codes::CODES.len());
        let eur = &value["EUR"];
        assert_eq!(eur["symbol"], "EUR");
        assert_eq!(eur["numeric_code"], "978");
        assert_eq!(eur["currency_symbol"], "€");
        assert!(eur["currency_symbol_narrow"].is_null());
        assert_eq!(eur["decimal_places"], 2);
        assert_eq!(eur["rounding"], 0);
        let eur_countries = country_codes(&eur["countries"]);
        assert!(eur_countries.contains(&"BG"));
        assert!(!eur_countries.contains(&"EA"));
        assert!(!eur_countries.contains(&"EU"));
        assert!(!eur_countries.contains(&"IC"));
        assert!(!eur_countries.contains(&"XK"));
        assert_eq!(value["JPY"]["decimal_places"], 0);
        assert_eq!(value["BGN"]["numeric_code"], "975");
        assert_eq!(country_codes(&value["HRK"]["countries"]), ["HR"]);
        assert!(!country_codes(&value["USD"]["countries"]).contains(&"ZW"));
        assert!(data.currencies(Some("dollar")).contains("\"USD\""));
        for row in &data.currencies {
            let row_value: serde_json::Value = serde_json::from_str(&row.slice).unwrap();
            assert!(row_value["currency_symbol_narrow"].is_null(), "{}", row.key);
            assert_eq!(row_value["rounding"], 0, "{}", row.key);
        }
    }

    fn country_codes(value: &serde_json::Value) -> Vec<&str> {
        value
            .as_array()
            .unwrap()
            .iter()
            .map(|code| code.as_str().unwrap())
            .collect()
    }

    #[test]
    fn countries_follow_the_libraries() {
        let data = StaticData::load().unwrap();
        let iso2s: Vec<&str> = data.countries.iter().map(|row| row.iso2.as_str()).collect();
        let mut sorted = iso2s.clone();
        sorted.sort_unstable();
        assert_eq!(iso2s, sorted);
        assert!(!iso2s.contains(&"EL"));
        assert!(!iso2s.contains(&"XK"));
        assert!(iso2s.contains(&"GR"));

        let de = row_json(&data, "DE");
        assert_eq!(de["currency"], "EUR");
        assert_eq!(de["tld"], ".de");
        assert_eq!(
            de["capital"],
            iso_rs::Country::from_alpha_2("DE").unwrap()[0]
                .capital
                .unwrap()
        );
        let gb = row_json(&data, "GB");
        assert_eq!(gb["currency"], "GBP");
        assert!(tld::exist("uk"));
        // tld 2.41 includes the reserved `gb` label, so the direct hit wins.
        assert!(tld::exist("gb"));
        assert_eq!(gb["tld"], ".gb");

        let mut saw_missing = false;
        for row in &data.countries {
            let value: serde_json::Value = serde_json::from_str(&row.slice).unwrap();
            let tld = value["tld"].as_str().unwrap();
            if let Some(label) = tld.strip_prefix('.') {
                assert!(tld::TLD.contains(label), "{label} for {}", row.iso2);
            } else {
                assert_eq!(tld, "", "{}", row.iso2);
                saw_missing = true;
            }
        }
        assert!(saw_missing, "expected a country with no IANA ccTLD");
        assert_ne!(row_json(&data, "BQ")["tld"], ".an");
        assert_ne!(row_json(&data, "UM")["tld"], ".us");

        let aq_capital = iso_rs::Country::from_alpha_2("AQ").unwrap()[0]
            .capital
            .unwrap_or("");
        assert_eq!(row_json(&data, "AQ")["capital"], aq_capital);

        let eur = data.countries(None, None, None, Some("eur"));
        assert!(eur.contains("\"iso2\":\"DE\""));
        assert!(!eur.contains("\"iso2\":\"GB\""));
    }

    fn row_json(data: &StaticData, iso2: &str) -> serde_json::Value {
        serde_json::from_str(data.country_slice(iso2).unwrap()).unwrap()
    }
}
