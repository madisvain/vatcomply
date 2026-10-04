//! Country from a configured CDN header, then an optional MaxMind database.

use std::net::IpAddr;
use std::path::Path;
use std::sync::Arc;

use maxminddb::Reader;
use serde::Deserialize;

#[derive(Clone)]
pub struct GeoDb {
    reader: Arc<Reader<Vec<u8>>>,
}

#[derive(Deserialize)]
struct CountryRecord {
    country: Option<CountryIso>,
}

#[derive(Deserialize)]
struct CountryIso {
    iso_code: Option<String>,
}

impl GeoDb {
    pub fn open(path: &Path) -> Result<Self, String> {
        let reader = Reader::open_readfile(path)
            .map_err(|error| format!("GEOIP_DB_PATH {}: {error}", path.display()))?;
        Ok(Self {
            reader: Arc::new(reader),
        })
    }

    pub fn iso_code(&self, ip: IpAddr) -> Option<String> {
        let record: CountryRecord = self.reader.lookup(ip).ok()?.decode().ok()??;
        let code = record.country.and_then(|country| country.iso_code)?;
        let code = code.trim().to_string();
        if code.is_empty() {
            None
        } else {
            Some(code.to_uppercase())
        }
    }
}
