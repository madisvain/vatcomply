//! ECB currency allow-list. Order is the `/currencies` key order and the
//! order used when a code is present on a rates row (after EUR).

pub const CODES: [&str; 33] = [
    "EUR", "USD", "JPY", "BGN", "CZK", "DKK", "GBP", "HUF", "PLN", "RON", "SEK", "CHF", "ISK",
    "NOK", "HRK", "RUB", "TRY", "AUD", "BRL", "CAD", "CNY", "HKD", "IDR", "ILS", "INR", "KRW",
    "MXN", "MYR", "NZD", "PHP", "SGD", "THB", "ZAR",
];

pub fn allowed(code: &str) -> bool {
    CODES.contains(&code)
}

pub const EU_VAT_MEMBERS: [&str; 27] = [
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IE", "IT",
    "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK",
];
