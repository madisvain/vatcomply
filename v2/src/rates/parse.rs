//! ECB eurofxref XML → decimal strings, in document order.

use quick_xml::events::Event;
use quick_xml::Reader;

use crate::codes;
use crate::date::Date;
use crate::rates::book::RateRow;
use crate::rates::pyfloat;

#[derive(Debug)]
pub struct ParseError {
    pub message: String,
}

impl ParseError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl std::fmt::Display for ParseError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.message)
    }
}

pub fn parse_ecb_xml(input: &[u8]) -> Result<Vec<RateRow>, ParseError> {
    let mut reader = Reader::from_reader(input);
    reader.config_mut().trim_text(true);
    let mut buf = Vec::new();
    let mut open: Option<RawDay> = None;
    let mut days: Vec<RawDay> = Vec::new();

    loop {
        let event = reader
            .read_event_into(&mut buf)
            .map_err(|error| ParseError::new(error.to_string()))?;
        match event {
            Event::Start(element) | Event::Empty(element) => {
                if !is_cube(element.name().as_ref()) {
                    buf.clear();
                    continue;
                }
                let mut time = None;
                let mut currency = None;
                let mut rate = None;
                for attribute in element.attributes() {
                    let attribute =
                        attribute.map_err(|error| ParseError::new(error.to_string()))?;
                    let value = attribute
                        .normalized_value(quick_xml::XmlVersion::Implicit1_0)
                        .map_err(|error| ParseError::new(error.to_string()))?;
                    match attribute.key.as_ref() {
                        b"time" => time = Some(value.into_owned()),
                        b"currency" => currency = Some(value.into_owned()),
                        b"rate" => rate = Some(value.into_owned()),
                        _ => {}
                    }
                }
                if let Some(time) = time {
                    if let Some(day) = open.take() {
                        days.push(day);
                    }
                    open = Some(RawDay {
                        date: time,
                        pairs: Vec::new(),
                    });
                } else if let (Some(currency), Some(rate), Some(day)) =
                    (currency, rate, open.as_mut())
                {
                    day.pairs.push((currency, rate));
                }
            }
            Event::Eof => break,
            _ => {}
        }
        buf.clear();
    }
    if let Some(day) = open.take() {
        days.push(day);
    }

    let mut rows = Vec::with_capacity(days.len());
    for day in days {
        let date = Date::parse(&day.date)
            .map_err(|_| ParseError::new(format!("invalid ECB date {}", day.date)))?;
        rows.push(RateRow::from_pairs(date, day.pairs)?);
    }
    rows.sort_by(|left, right| left.date.cmp(&right.date));
    // `sort_by` is stable, so the later cube in the file is the later duplicate.
    rows.dedup_by(|kept, candidate| {
        if kept.date == candidate.date {
            *kept = candidate.clone();
            true
        } else {
            false
        }
    });
    Ok(rows)
}

struct RawDay {
    date: String,
    pairs: Vec<(String, String)>,
}

fn is_cube(name: &[u8]) -> bool {
    name == b"Cube" || name.ends_with(b":Cube")
}

impl RateRow {
    pub fn from_pairs(date: Date, pairs: Vec<(String, String)>) -> Result<Self, ParseError> {
        let mut codes_out = Vec::new();
        let mut decimals = Vec::new();
        let mut tokens = Vec::new();
        for (code, decimal) in pairs {
            if !codes::allowed(&code) {
                continue;
            }
            let token = pyfloat::ecb_token(&decimal)
                .map_err(|_| ParseError::new(format!("invalid rate {code}={decimal} on {date}")))?;
            codes_out.push(code);
            decimals.push(decimal);
            tokens.push(token);
        }
        Ok(Self {
            date,
            codes: codes_out,
            decimals,
            tokens,
        })
    }
}
