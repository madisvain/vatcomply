//! In-memory ECB book and the `/rates` renderer.
//!
//! Decimal strings stay decimal. JSON number text comes from `pyfloat`.

use axum::http::StatusCode;
use bytes::Bytes;

use crate::codes;
use crate::date::Date;
use crate::error::ApiError;
use crate::rates::pyfloat;

#[derive(Clone, Debug)]
pub struct RateRow {
    pub date: Date,
    pub codes: Vec<String>,
    pub decimals: Vec<String>,
    pub tokens: Vec<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RateSource {
    Embedded,
    Disk,
    Ecb,
}

impl RateSource {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Embedded => "embedded",
            Self::Disk => "disk",
            Self::Ecb => "ecb",
        }
    }
}

#[derive(Clone, Debug)]
pub struct RateBook {
    pub rows: Vec<RateRow>,
    pub source: RateSource,
    pub fetched_at: String,
    pub latest_eur: Bytes,
}

impl RateBook {
    pub fn from_rows(
        mut rows: Vec<RateRow>,
        source: RateSource,
        fetched_at: String,
    ) -> Result<Self, String> {
        rows.sort_by(|left, right| left.date.cmp(&right.date));
        // `dedup_by` removes the first argument when the predicate is true.
        // That argument is the later row, so copy it onto the kept row.
        rows.dedup_by(|later, earlier| {
            if later.date == earlier.date {
                *earlier = later.clone();
                true
            } else {
                false
            }
        });
        let latest = rows
            .last()
            .ok_or_else(|| "rate book is empty".to_string())?;
        let latest_eur =
            Bytes::from(render_row(latest, "EUR", None).map_err(|error| error.detail)?);
        Ok(Self {
            rows,
            source,
            fetched_at,
            latest_eur,
        })
    }

    pub fn latest_date(&self) -> Option<Date> {
        self.rows.last().map(|row| row.date)
    }

    /// Latest stored date on or before `query`.
    pub fn lookup(&self, query: Date) -> Option<&RateRow> {
        let index = self.rows.partition_point(|row| row.date <= query);
        if index == 0 {
            None
        } else {
            self.rows.get(index - 1)
        }
    }

    /// Insert missing days and overwrite days that are already present.
    pub fn merge(&mut self, incoming: Vec<RateRow>) -> Result<(), String> {
        for row in incoming {
            match self.rows.binary_search_by(|item| item.date.cmp(&row.date)) {
                Ok(index) => self.rows[index] = row,
                Err(index) => self.rows.insert(index, row),
            }
        }
        let latest = self
            .rows
            .last()
            .ok_or_else(|| "rate book is empty".to_string())?;
        self.latest_eur =
            Bytes::from(render_row(latest, "EUR", None).map_err(|error| error.detail)?);
        Ok(())
    }
}

pub struct RatesQuery<'a> {
    /// `None` when the parameter is absent. `Some("")` is the empty value.
    pub base: Option<&'a str>,
    pub symbols: Option<&'a str>,
    pub date_raw: Option<&'a str>,
}

pub fn answer(book: &RateBook, query: RatesQuery<'_>, today: Date) -> Result<Bytes, ApiError> {
    let base = query.base.unwrap_or("EUR");
    if !codes::allowed(base) {
        return Err(ApiError::new(
            StatusCode::BAD_REQUEST,
            format!("Base currency '{base}' is not supported."),
        ));
    }
    let symbols = match query.symbols {
        None | Some("") => None,
        Some(raw) => {
            let list: Vec<&str> = raw.split(',').collect();
            for symbol in &list {
                if !codes::allowed(symbol) {
                    return Err(ApiError::new(
                        StatusCode::BAD_REQUEST,
                        format!("Currency '{symbol}' is not supported."),
                    ));
                }
            }
            Some(list)
        }
    };
    let query_date = match query.date_raw {
        None | Some("") => today,
        Some(text) => parse_query_date(text)?,
    };
    let row = book.lookup(query_date).ok_or_else(|| {
        ApiError::new(
            StatusCode::NOT_FOUND,
            "No rate data available for the specified date.",
        )
    })?;
    if base == "EUR" && symbols.is_none() && Some(row.date) == book.latest_date() {
        return Ok(book.latest_eur.clone());
    }
    render_row(row, base, symbols.as_deref()).map(Bytes::from)
}

fn parse_query_date(text: &str) -> Result<Date, ApiError> {
    if !is_ymd_shape(text) {
        return Err(ApiError::new(
            StatusCode::BAD_REQUEST,
            format!("Invalid date format: '{text}'. Expected format: YYYY-MM-DD"),
        ));
    }
    Date::parse(text).map_err(|_| {
        ApiError::new(
            StatusCode::BAD_REQUEST,
            format!("Invalid date: '{text}'. Expected a valid date in YYYY-MM-DD format."),
        )
    })
}

fn is_ymd_shape(text: &str) -> bool {
    let bytes = text.as_bytes();
    bytes.len() == 10
        && bytes[4] == b'-'
        && bytes[7] == b'-'
        && bytes
            .iter()
            .enumerate()
            .all(|(index, byte)| index == 4 || index == 7 || byte.is_ascii_digit())
}

fn render_row(row: &RateRow, base: &str, symbols: Option<&[&str]>) -> Result<String, ApiError> {
    let mut items: Vec<(&str, String)> = Vec::with_capacity(row.codes.len() + 1);
    if base == "EUR" {
        items.push(("EUR", "1.0".to_string()));
        for (code, token) in row.codes.iter().zip(row.tokens.iter()) {
            items.push((code.as_str(), token.clone()));
        }
    } else {
        let base_decimal = row
            .codes
            .iter()
            .zip(row.decimals.iter())
            .find(|(code, _)| code.as_str() == base)
            .map(|(_, decimal)| decimal.as_str());
        let Some(base_decimal) = base_decimal else {
            return Err(ApiError::new(
                StatusCode::BAD_REQUEST,
                format!("Base currency '{base}' not available in current rates data"),
            ));
        };
        let euro = pyfloat::cross_token("1", base_decimal).map_err(|_| internal("cross rate"))?;
        items.push(("EUR", euro));
        for (code, decimal) in row.codes.iter().zip(row.decimals.iter()) {
            let token =
                pyfloat::cross_token(decimal, base_decimal).map_err(|_| internal("cross rate"))?;
            items.push((code.as_str(), token));
        }
    }
    if let Some(symbols) = symbols {
        items.retain(|(code, _)| symbols.iter().any(|symbol| symbol == code));
    }
    let mut body = String::with_capacity(48 + items.len() * 16);
    body.push_str("{\"date\":\"");
    body.push_str(&row.date.to_string());
    body.push_str("\",\"base\":\"");
    body.push_str(base);
    body.push_str("\",\"rates\":{");
    for (index, (code, token)) in items.iter().enumerate() {
        if index > 0 {
            body.push(',');
        }
        body.push('"');
        body.push_str(code);
        body.push_str("\":");
        body.push_str(token);
    }
    body.push_str("}}");
    Ok(body)
}

fn internal(message: &str) -> ApiError {
    tracing::error!(message, "rate render failed");
    ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "Internal Server Error")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rates::parse::parse_ecb_xml;

    fn book() -> RateBook {
        let rows = parse_ecb_xml(include_bytes!("../../tests/fixtures/ecb/excerpt.xml")).unwrap();
        RateBook::from_rows(rows, RateSource::Embedded, "2026-10-04T00:00:00Z".into()).unwrap()
    }

    #[test]
    fn weekend_and_cross_rate() {
        let book = book();
        let today = Date::parse("2026-10-04").unwrap();
        let body = answer(
            &book,
            RatesQuery {
                base: Some("USD"),
                symbols: Some("EUR,GBP"),
                date_raw: Some("2018-10-13"),
            },
            today,
        )
        .unwrap();
        assert_eq!(
            body.as_ref(),
            br#"{"date":"2018-10-12","base":"USD","rates":{"EUR":0.864006,"GBP":0.757214}}"#
        );
    }

    #[test]
    fn merge_inserts_and_overwrites() {
        let mut book = book();
        let before = book.rows.len();
        let xml = br#"<?xml version="1.0"?>
<Cube>
<Cube time="2026-10-02"><Cube currency="USD" rate="9.9999"/></Cube>
<Cube time="2026-10-01"><Cube currency="USD" rate="1.1000"/></Cube>
</Cube>"#;
        book.merge(parse_ecb_xml(xml).unwrap()).unwrap();
        assert_eq!(book.rows.len(), before + 1);
        let overwritten = book.lookup(Date::parse("2026-10-02").unwrap()).unwrap();
        assert_eq!(overwritten.decimals, ["9.9999".to_string()]);
        let inserted = book.lookup(Date::parse("2026-10-01").unwrap()).unwrap();
        assert_eq!(inserted.date.to_string(), "2026-10-01");
        assert_eq!(inserted.decimals, ["1.1000".to_string()]);
    }

    #[test]
    fn missing_base_on_row() {
        let book = book();
        let error = answer(
            &book,
            RatesQuery {
                base: Some("BGN"),
                symbols: None,
                date_raw: Some("2026-10-02"),
            },
            Date::parse("2026-10-04").unwrap(),
        )
        .unwrap_err();
        assert_eq!(error.status, StatusCode::BAD_REQUEST);
        assert_eq!(
            error.detail,
            "Base currency 'BGN' not available in current rates data"
        );
    }
}
