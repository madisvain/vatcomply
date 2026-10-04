//! Versioned, checksummed rate snapshots.
//!
//! On disk and inside the binary the bytes are gzip of:
//!
//! ```text
//! VATSNAP1\n
//! <sha256 hex of the JSON body>\n
//! <JSON body>
//! ```
//!
//! The JSON keeps ECB decimal strings. EUR is not stored.

use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::Path;

use flate2::read::GzDecoder;
use flate2::write::GzEncoder;
use flate2::Compression;
use sha2::{Digest, Sha256};

use crate::date::Date;
use crate::rates::book::{RateBook, RateRow, RateSource};
use crate::rates::parse::ParseError;

const EMBEDDED: &[u8] = include_bytes!("../../data/rates-snapshot.json.gz");
const MAGIC: &[u8] = b"VATSNAP1\n";

pub struct Loaded {
    pub book: RateBook,
    /// A disk snapshot verified, even when it is older than the embedded one.
    pub disk_valid: bool,
}

pub fn load_initial(data_dir: &Path) -> Result<Loaded, String> {
    let embedded = decode_gzip(EMBEDDED, RateSource::Embedded)
        .map_err(|error| format!("embedded rates snapshot: {error}"))?;
    let embedded_date = embedded.latest_date();
    let path = data_dir.join("rates-snapshot.json.gz");
    match fs::read(&path) {
        Ok(bytes) => match decode_gzip(&bytes, RateSource::Disk) {
            Ok(disk) => {
                let use_disk = disk.latest_date() >= embedded_date;
                if use_disk {
                    tracing::info!(
                        path = %path.display(),
                        date = %disk.latest_date().map(|date| date.to_string()).unwrap_or_default(),
                        "loaded rates from disk snapshot"
                    );
                    Ok(Loaded {
                        book: disk,
                        disk_valid: true,
                    })
                } else {
                    tracing::info!("disk rates snapshot is older than the embedded snapshot");
                    Ok(Loaded {
                        book: embedded,
                        disk_valid: true,
                    })
                }
            }
            Err(error) => {
                tracing::error!(error = %error, path = %path.display(), "ignoring corrupt rates snapshot");
                Ok(Loaded {
                    book: embedded,
                    disk_valid: false,
                })
            }
        },
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(Loaded {
            book: embedded,
            disk_valid: false,
        }),
        Err(error) => {
            tracing::error!(error = %error, path = %path.display(), "ignoring unreadable rates snapshot");
            Ok(Loaded {
                book: embedded,
                disk_valid: false,
            })
        }
    }
}

pub fn write_snapshot(dir: &Path, book: &RateBook) -> Result<(), String> {
    fs::create_dir_all(dir).map_err(|error| format!("create {}: {error}", dir.display()))?;
    let bytes = encode(book)?;
    let tmp = dir.join(format!(".rates-snapshot.{}.tmp", std::process::id()));
    {
        let mut file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(&tmp)
            .map_err(|error| format!("open {}: {error}", tmp.display()))?;
        file.write_all(&bytes)
            .map_err(|error| format!("write {}: {error}", tmp.display()))?;
        file.sync_all()
            .map_err(|error| format!("sync {}: {error}", tmp.display()))?;
    }
    let dest = dir.join("rates-snapshot.json.gz");
    fs::rename(&tmp, &dest)
        .map_err(|error| format!("rename {} to {}: {error}", tmp.display(), dest.display()))?;
    Ok(())
}

pub fn encode(book: &RateBook) -> Result<Vec<u8>, String> {
    let body = encode_json(book);
    let framed = frame(body.as_bytes());
    let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
    encoder
        .write_all(&framed)
        .map_err(|error| format!("gzip snapshot: {error}"))?;
    encoder
        .finish()
        .map_err(|error| format!("gzip snapshot: {error}"))
}

fn encode_json(book: &RateBook) -> String {
    let mut dates = String::from("[");
    for (index, row) in book.rows.iter().enumerate() {
        if index > 0 {
            dates.push(',');
        }
        dates.push('[');
        push_json_string(&mut dates, &row.date.to_string());
        dates.push_str(",[");
        for (pair_index, (code, decimal)) in row.codes.iter().zip(row.decimals.iter()).enumerate() {
            if pair_index > 0 {
                dates.push(',');
            }
            dates.push('[');
            push_json_string(&mut dates, code);
            dates.push(',');
            push_json_string(&mut dates, decimal);
            dates.push(']');
        }
        dates.push_str("]]");
    }
    dates.push(']');
    let mut body = String::from("{\"version\":1,\"generated_at\":");
    push_json_string(&mut body, &book.fetched_at);
    body.push_str(",\"dates\":");
    body.push_str(&dates);
    body.push('}');
    body
}

fn frame(body: &[u8]) -> Vec<u8> {
    let mut raw = Vec::with_capacity(MAGIC.len() + 65 + body.len());
    raw.extend_from_slice(MAGIC);
    raw.extend_from_slice(sha256_hex(body).as_bytes());
    raw.push(b'\n');
    raw.extend_from_slice(body);
    raw
}

fn decode_gzip(gzipped: &[u8], source: RateSource) -> Result<RateBook, String> {
    let mut decoder = GzDecoder::new(gzipped);
    let mut raw = Vec::new();
    decoder
        .read_to_end(&mut raw)
        .map_err(|error| format!("gunzip: {error}"))?;
    decode_framed(&raw, source)
}

fn decode_framed(raw: &[u8], source: RateSource) -> Result<RateBook, String> {
    let rest = raw
        .strip_prefix(MAGIC)
        .ok_or_else(|| "rates snapshot magic mismatch".to_string())?;
    let split = rest
        .iter()
        .position(|byte| *byte == b'\n')
        .ok_or_else(|| "rates snapshot is missing a checksum line".to_string())?;
    let hex =
        std::str::from_utf8(&rest[..split]).map_err(|_| "checksum is not utf-8".to_string())?;
    let body = &rest[split + 1..];
    let actual = sha256_hex(body);
    if actual != hex {
        return Err("rates snapshot checksum mismatch".to_string());
    }
    rows_from_json(body, source)
}

fn rows_from_json(body: &[u8], source: RateSource) -> Result<RateBook, String> {
    let value: serde_json::Value =
        serde_json::from_slice(body).map_err(|error| format!("snapshot json: {error}"))?;
    let version = value
        .get("version")
        .and_then(|item| item.as_u64())
        .ok_or_else(|| "snapshot version missing".to_string())?;
    if version != 1 {
        return Err(format!("unsupported snapshot version {version}"));
    }
    let generated_at = value
        .get("generated_at")
        .and_then(|item| item.as_str())
        .unwrap_or("1970-01-01T00:00:00Z")
        .to_string();
    let dates = value
        .get("dates")
        .and_then(|item| item.as_array())
        .ok_or_else(|| "snapshot dates missing".to_string())?;
    let mut rows = Vec::with_capacity(dates.len());
    for day in dates {
        let pair = day
            .as_array()
            .ok_or_else(|| "snapshot day is not an array".to_string())?;
        let date_text = pair
            .first()
            .and_then(|item| item.as_str())
            .ok_or_else(|| "snapshot day is missing a date".to_string())?;
        let date = Date::parse(date_text).map_err(|_| format!("snapshot date {date_text}"))?;
        let pairs_json = pair
            .get(1)
            .and_then(|item| item.as_array())
            .ok_or_else(|| format!("snapshot pairs missing for {date_text}"))?;
        let mut pairs = Vec::with_capacity(pairs_json.len());
        for item in pairs_json {
            let entry = item
                .as_array()
                .ok_or_else(|| "snapshot pair is not an array".to_string())?;
            let code = entry
                .first()
                .and_then(|value| value.as_str())
                .ok_or_else(|| "snapshot currency code missing".to_string())?;
            let decimal = entry
                .get(1)
                .and_then(|value| value.as_str())
                .ok_or_else(|| "snapshot rate missing".to_string())?;
            pairs.push((code.to_string(), decimal.to_string()));
        }
        let row = RateRow::from_pairs(date, pairs).map_err(|error: ParseError| error.message)?;
        rows.push(row);
    }
    RateBook::from_rows(rows, source, generated_at)
}

pub fn sha256_hex(data: &[u8]) -> String {
    let digest = Sha256::digest(data);
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(digest.len() * 2);
    for byte in digest {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

fn push_json_string(out: &mut String, value: &str) {
    out.push('"');
    for char in value.chars() {
        match char {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            other => out.push(other),
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rates::parse::parse_ecb_xml;

    #[test]
    fn embedded_snapshot_loads() {
        let loaded = load_initial(Path::new("/nonexistent/vatcomply-v2-snapshot")).unwrap();
        assert!(!loaded.disk_valid);
        assert_eq!(loaded.book.source, RateSource::Embedded);
        assert!(loaded.book.latest_date().unwrap() >= Date::parse("2026-10-02").unwrap());
    }

    #[test]
    fn round_trip_and_corrupt_disk() {
        let rows = parse_ecb_xml(include_bytes!("../../tests/fixtures/ecb/excerpt.xml")).unwrap();
        let book =
            RateBook::from_rows(rows, RateSource::Ecb, "2026-10-04T00:00:00Z".into()).unwrap();
        let encoded = encode(&book).unwrap();
        let decoded = decode_gzip(&encoded, RateSource::Disk).unwrap();
        assert_eq!(decoded.rows.len(), book.rows.len());
        assert_eq!(decoded.latest_date(), book.latest_date());
        assert_eq!(decoded.rows[0].decimals, book.rows[0].decimals);

        let dir = std::env::temp_dir().join(format!("vatcomply-snap-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        fs::write(dir.join("rates-snapshot.json.gz"), b"not a snapshot").unwrap();
        let loaded = load_initial(&dir).unwrap();
        assert!(!loaded.disk_valid);
        assert_eq!(loaded.book.source, RateSource::Embedded);
        let _ = fs::remove_dir_all(&dir);
    }
}
