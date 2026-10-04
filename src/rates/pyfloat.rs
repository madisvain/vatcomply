//! CPython-compatible JSON numbers for ECB rates.
//!
//! This is the only module that uses `f64`. Storage stays a decimal string.
//! The EUR-base token is `json.dumps(float(ecb_string))`. A cross rate follows
//! `vatcomply/api.py`: `float(round(Decimal(str(float(rate))) / Decimal(str(float(base))), 6))`
//! with `ROUND_HALF_EVEN`, then `json.dumps` of that float. EUR's numerator is
//! `Decimal("1")`, not `Decimal(str(float(1)))` — they are equal, and the code
//! overwrites the euro entry with the former.

use rust_decimal::Decimal;
use rust_decimal::RoundingStrategy;
use std::str::FromStr;

#[allow(clippy::result_unit_err)]
pub fn ecb_token(decimal: &str) -> Result<String, ()> {
    let value = parse_finite(decimal)?;
    Ok(json_token(value))
}

#[allow(clippy::result_unit_err)]
pub fn cross_token(rate_decimal: &str, base_decimal: &str) -> Result<String, ()> {
    let base = decimal_via_float(base_decimal)?;
    let numer = if rate_decimal == "1" {
        Decimal::from_str("1").map_err(|_| ())?
    } else {
        decimal_via_float(rate_decimal)?
    };
    let quotient = numer.checked_div(base).ok_or(())?;
    let rounded = quotient.round_dp_with_strategy(6, RoundingStrategy::MidpointNearestEven);
    let as_float: f64 = rounded.to_string().parse().map_err(|_| ())?;
    if !as_float.is_finite() {
        return Err(());
    }
    Ok(json_token(as_float))
}

fn decimal_via_float(decimal: &str) -> Result<Decimal, ()> {
    // `str(float(s))` and CPython `json.dumps` agree on the oracle set.
    let token = json_token(parse_finite(decimal)?);
    Decimal::from_str(&token).map_err(|_| ())
}

fn parse_finite(decimal: &str) -> Result<f64, ()> {
    let value: f64 = decimal.parse().map_err(|_| ())?;
    if value.is_finite() {
        Ok(value)
    } else {
        Err(())
    }
}

/// CPython `json.dumps(float)` is `float.__repr__`: Rust's debug float, with
/// the exponent written as `e+NN` / `e-NN` (sign, at least two digits).
fn json_token(value: f64) -> String {
    let raw = format!("{value:?}");
    let Some((mantissa, exponent)) = raw.split_once('e') else {
        return raw;
    };
    let Ok(exponent) = exponent.parse::<i32>() else {
        return raw;
    };
    let sign = if exponent < 0 { '-' } else { '+' };
    format!("{mantissa}e{sign}{:02}", exponent.unsigned_abs())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn eur_base_tokens() {
        assert_eq!(ecb_token("137").unwrap(), "137.0");
        assert_eq!(ecb_token("1.9558").unwrap(), "1.9558");
        assert_eq!(ecb_token("1.1225").unwrap(), "1.1225");
        assert_eq!(ecb_token("20149.32").unwrap(), "20149.32");
    }

    #[test]
    fn matches_full_oracle() {
        let raw = include_str!("../../tests/fixtures/pyfloat_oracle.json");
        let value: serde_json::Value = serde_json::from_str(raw).unwrap();
        let tokens = value["tokens"].as_object().unwrap();
        assert!(tokens.len() > 100_000);
        for (decimal, token) in tokens {
            assert_eq!(
                ecb_token(decimal).unwrap(),
                token.as_str().unwrap(),
                "{decimal}"
            );
        }
        let cross = value["cross"].as_array().unwrap();
        assert!(cross.len() > 100);
        for item in cross {
            let base = item["base"].as_str().unwrap();
            let rate = item["rate"].as_str().unwrap();
            let token = item["token"].as_str().unwrap();
            assert_eq!(cross_token(rate, base).unwrap(), token, "{rate}/{base}");
        }
    }

    #[test]
    fn cross_rates_from_production() {
        assert_eq!(cross_token("1", "1.1574").unwrap(), "0.864006");
        assert_eq!(cross_token("0.8764", "1.1574").unwrap(), "0.757214");
        assert_eq!(cross_token("1", "7.5365").unwrap(), "0.132688");
        assert_eq!(cross_token("1.0666", "7.5365").unwrap(), "0.141525");
        assert_eq!(cross_token("1", "1.9558").unwrap(), "0.5113");
        assert_eq!(cross_token("1.175", "1.9558").unwrap(), "0.600777");
    }
}
