//! Query strings the way Django's `QueryDict` reads them: `+` is a space,
//! percent-decoding is lossy UTF-8, and the last duplicate key wins.

use std::collections::HashMap;

pub fn last(query: Option<&str>) -> HashMap<String, String> {
    let mut map = HashMap::new();
    let Some(query) = query else {
        return map;
    };
    for pair in query.split('&') {
        if pair.is_empty() {
            continue;
        }
        let (key, value) = pair.split_once('=').unwrap_or((pair, ""));
        map.insert(decode(key), decode(value));
    }
    map
}

pub fn decode(input: &str) -> String {
    let bytes = input.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        match bytes[index] {
            b'+' => {
                out.push(b' ');
                index += 1;
            }
            b'%' if index + 2 < bytes.len() => {
                let hex = &input[index + 1..index + 3];
                match u8::from_str_radix(hex, 16) {
                    Ok(value) => out.push(value),
                    Err(_) => {
                        out.push(b'%');
                        out.push(bytes[index + 1]);
                        out.push(bytes[index + 2]);
                    }
                }
                index += 3;
            }
            byte => {
                out.push(byte);
                index += 1;
            }
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}

/// Redact `vat_number` and `iban` so request logs never carry the full value.
pub fn redact(query: &str) -> String {
    let mut parts = Vec::new();
    for pair in query.split('&') {
        let (key, value) = pair.split_once('=').unwrap_or((pair, ""));
        let decoded_key = decode(key);
        if decoded_key == "vat_number" {
            let decoded = decode(value);
            let prefix = decoded.chars().take(2).collect::<String>();
            parts.push(format!("{decoded_key}={prefix}***"));
        } else if decoded_key == "iban" {
            parts.push(format!("{decoded_key}=***"));
        } else {
            parts.push(pair.to_string());
        }
    }
    parts.join("&")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn last_duplicate_wins_and_plus_is_space() {
        let map = last(Some("base=USD&base=EUR&symbols=USD,+JPY"));
        assert_eq!(map.get("base").map(String::as_str), Some("EUR"));
        assert_eq!(map.get("symbols").map(String::as_str), Some("USD, JPY"));
    }

    #[test]
    fn redacts_vat_and_iban() {
        let text = redact("vat_number=DE123456789&iban=DE89370400440532013000&base=EUR");
        assert!(!text.contains("DE123456789"));
        assert!(!text.contains("DE89370400440532013000"));
        assert!(text.contains("vat_number=DE***"));
        assert!(text.contains("iban=***"));
        assert!(text.contains("base=EUR"));
    }
}
