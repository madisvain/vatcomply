---
title: Foreign Exchange Rates
description: "Free exchange rates API — daily and historical foreign exchange rates for 33 currencies from the ECB. Base currency conversion and symbol filtering. No API key."
icon: lucide/arrow-left-right
---

# Foreign Exchange Rates

Get daily foreign exchange rates from the European Central Bank, including historical data.

## Latest Rates

```http
GET https://api.vatcomply.com/rates
```

### Response

```json
{
  "date": "2024-01-15",
  "base": "EUR",
  "rates": {
    "USD": 1.0856,
    "GBP": 0.8642,
    "JPY": 156.92
  }
}
```

## Parameters

| Parameter | Type   | Required | Description                                      |
|-----------|--------|----------|--------------------------------------------------|
| `base`    | string | No       | Base currency for conversion (default: `EUR`)     |
| `symbols` | string | No       | Comma-separated list of currencies to return      |
| `date`    | string | No       | Date for historical rates in `YYYY-MM-DD` format  |

## Response Fields

| Field   | Type   | Description                                    |
|---------|--------|------------------------------------------------|
| `date`  | string | Date of the rates in `YYYY-MM-DD` format       |
| `base`  | string | Base currency code                             |
| `rates` | object | Exchange rates keyed by currency code (see structure below) |

### `rates` object

Each key is a 3-letter currency code and the value is the exchange rate as a number relative to the `base` currency.

```json
{
  "<CURRENCY_CODE>": <number>,
  ...
}
```

For example, with `base=EUR`:

| Key   | Value    | Meaning                    |
|-------|----------|----------------------------|
| `USD` | `1.0856` | 1 EUR = 1.0856 USD         |
| `GBP` | `0.8642` | 1 EUR = 0.8642 GBP         |
| `JPY` | `156.92` | 1 EUR = 156.92 JPY         |

See the full list of [supported currencies](#supported-currencies) below.

## Supported Currencies

The rates are sourced from the European Central Bank and cover the following 33 currencies:

| Code | Currency               | Code | Currency               |
|------|------------------------|------|------------------------|
| EUR  | Euro (base)            | INR  | Indian Rupee           |
| USD  | US Dollar              | KRW  | South Korean Won       |
| JPY  | Japanese Yen           | MXN  | Mexican Peso           |
| BGN  | Bulgarian Lev          | MYR  | Malaysian Ringgit      |
| CZK  | Czech Koruna           | NZD  | New Zealand Dollar     |
| DKK  | Danish Krone           | PHP  | Philippine Peso        |
| GBP  | British Pound          | SGD  | Singapore Dollar       |
| HUF  | Hungarian Forint       | THB  | Thai Baht              |
| PLN  | Polish Zloty           | ZAR  | South African Rand     |
| RON  | Romanian Leu           | HRK  | Croatian Kuna ^1^      |
| SEK  | Swedish Krona          | RUB  | Russian Ruble ^2^      |
| CHF  | Swiss Franc            |      |                        |
| ISK  | Icelandic Krona        |      |                        |
| NOK  | Norwegian Krone        |      |                        |
| TRY  | Turkish Lira           |      |                        |
| AUD  | Australian Dollar      |      |                        |
| BRL  | Brazilian Real         |      |                        |
| CAD  | Canadian Dollar        |      |                        |
| CNY  | Chinese Yuan           |      |                        |
| HKD  | Hong Kong Dollar       |      |                        |
| IDR  | Indonesian Rupiah      |      |                        |
| ILS  | Israeli New Shekel     |      |                        |

1. HRK - Historical only. Croatia joined the Eurozone in 2023.
2. RUB - Historical only. Suspended due to sanctions in 2022.

## Base Currency Conversion

Return rates relative to a specific base currency.

```http
GET https://api.vatcomply.com/rates?base=USD
```

## Specific Currencies

Filter the response to only include specific currencies.

```http
GET https://api.vatcomply.com/rates?symbols=USD,GBP
```

## Historical Rates

Retrieve rates for a specific date.

```http
GET https://api.vatcomply.com/rates?date=2018-01-01
```

## Combined Parameters

All parameters can be combined in a single request.

```http
GET https://api.vatcomply.com/rates?date=2018-01-01&symbols=USD,GBP&base=EUR
```

## Error Responses

**400 - Unsupported base currency:**

```json
{
  "error": "Base currency 'XYZ' is not supported."
}
```

**400 - Unsupported symbol:**

```json
{
  "error": "Currency 'XYZ' is not supported."
}
```

**400 - Invalid date format:**

```json
{
  "error": "Invalid date format: 'not-a-date'. Expected format: YYYY-MM-DD"
}
```

**404 - No data available:**

```json
{
  "error": "No rate data available for the specified date."
}
```
