//! Civil dates without a calendar crate. ECB dates and query dates are both `YYYY-MM-DD`.

use std::fmt;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub struct Date {
    pub year: u16,
    pub month: u8,
    pub day: u8,
}

impl Date {
    #[allow(clippy::result_unit_err)]
    pub fn parse(text: &str) -> Result<Self, ()> {
        let bytes = text.as_bytes();
        if bytes.len() != 10 || bytes[4] != b'-' || bytes[7] != b'-' {
            return Err(());
        }
        if !bytes[..4].iter().all(u8::is_ascii_digit)
            || !bytes[5..7].iter().all(u8::is_ascii_digit)
            || !bytes[8..].iter().all(u8::is_ascii_digit)
        {
            return Err(());
        }
        let year: u16 = text[..4].parse().map_err(|_| ())?;
        let month: u8 = text[5..7].parse().map_err(|_| ())?;
        let day: u8 = text[8..].parse().map_err(|_| ())?;
        if month == 0 || month > 12 || day == 0 || day > days_in_month(year, month) {
            return Err(());
        }
        Ok(Self { year, month, day })
    }

    pub fn to_unix_days(self) -> i64 {
        let mut year = self.year as i64;
        let month = self.month as u64;
        if month <= 2 {
            year -= 1;
        }
        let era = if year >= 0 { year } else { year - 399 } / 400;
        let year_of_era = (year - era * 400) as u64;
        let month_prime = if month > 2 { month - 3 } else { month + 9 };
        let day_of_year = (153 * month_prime + 2) / 5 + self.day as u64 - 1;
        let day_of_era = year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
        era * 146097 + day_of_era as i64 - 719468
    }

    pub fn age_secs(self, now_unix: u64) -> u64 {
        let midnight = self.to_unix_days().max(0) as u64 * 86_400;
        now_unix.saturating_sub(midnight)
    }
}

impl fmt::Display for Date {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{:04}-{:02}-{:02}",
            self.year, self.month, self.day
        )
    }
}

pub fn utc_today() -> Date {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0);
    from_unix_days((secs / 86_400) as i64)
}

pub fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0)
}

pub fn format_unix(secs: u64) -> String {
    let date = from_unix_days((secs / 86_400) as i64);
    let time_of_day = secs % 86_400;
    let hour = time_of_day / 3600;
    let minute = (time_of_day % 3600) / 60;
    let second = time_of_day % 60;
    format!("{date}T{hour:02}:{minute:02}:{second:02}Z")
}

pub fn from_unix_days(mut z: i64) -> Date {
    z += 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let day_of_era = (z - era * 146_097) as u64;
    let year_of_era =
        (day_of_era - day_of_era / 1460 + day_of_era / 36524 - day_of_era / 146_096) / 365;
    let mut year = year_of_era as i64 + era * 400;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let month_prime = (5 * day_of_year + 2) / 153;
    let day = day_of_year - (153 * month_prime + 2) / 5 + 1;
    let month = if month_prime < 10 {
        month_prime + 3
    } else {
        month_prime - 9
    };
    if month <= 2 {
        year += 1;
    }
    Date {
        year: year as u16,
        month: month as u8,
        day: day as u8,
    }
}

fn days_in_month(year: u16, month: u8) -> u8 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 => {
            if is_leap(year) {
                29
            } else {
                28
            }
        }
        _ => 0,
    }
}

fn is_leap(year: u16) -> bool {
    let year = year as u32;
    (year.is_multiple_of(4) && !year.is_multiple_of(100)) || year.is_multiple_of(400)
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn round_trips_real_days(year in 1999u16..2100, month in 1u8..=12, day in 1u8..=28) {
            let text = format!("{year:04}-{month:02}-{day:02}");
            let parsed = Date::parse(&text).unwrap();
            prop_assert_eq!(parsed.to_string(), text);
        }

        #[test]
        fn rejects_month_zero(year in 1999u16..2100, day in 1u8..=28) {
            let text = format!("{year:04}-00-{day:02}");
            prop_assert!(Date::parse(&text).is_err());
        }
    }

    #[test]
    fn unix_epoch_and_known_days() {
        assert_eq!(from_unix_days(0), Date::parse("1970-01-01").unwrap());
        assert_eq!(Date::parse("1970-01-01").unwrap().to_unix_days(), 0);
        assert_eq!(Date::parse("1999-01-04").unwrap().to_string(), "1999-01-04");
        assert_eq!(Date::parse("2024-02-29").unwrap().day, 29);
        assert!(Date::parse("2024-02-30").is_err());
        assert!(Date::parse("2024-1-01").is_err());
        assert!(Date::parse("1999-13-01").is_err());
        let day = Date::parse("2026-10-04").unwrap();
        assert_eq!(from_unix_days(day.to_unix_days()), day);
    }
}
