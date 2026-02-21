---
title: Currencies
description: Information about all supported currencies
icon: lucide/coins
---

# Currencies

Retrieve information about all supported currencies.

## Endpoint

```http
GET /currencies
```

## Parameters

| Parameter | Required | Description                                      |
|-----------|----------|--------------------------------------------------|
| `search`  | no       | Filter currencies by code or name (case-insensitive) |

When `search` is omitted, all currencies are returned.

## Response Fields

The response is a JSON object keyed by currency code. Each value contains:

| Field                   | Type         | Description                                                    |
|-------------------------|--------------|----------------------------------------------------------------|
| `name`                  | string       | Full currency name                                             |
| `symbol`                | string       | Currency code (e.g. `EUR`)                                     |
| `numeric_code`          | string       | ISO 4217 numeric code (e.g. `"840"` for USD)                  |
| `currency_symbol`       | string       | Locale-specific currency symbol (e.g. `"$"` for USD)          |
| `currency_symbol_narrow`| string\|null | Narrow currency symbol variant, or `null` if unavailable      |
| `decimal_places`        | integer      | Number of decimal places (e.g. `2` for USD, `0` for JPY)      |
| `rounding`              | integer      | Rounding increment (usually `0`)                               |
| `countries`             | array        | ISO 3166-1 alpha-2 codes of countries using this currency      |
| `official_countries`    | array        | Countries where this currency is legal tender                  |
| `historical`            | boolean      | `true` if the currency is no longer in active use              |

## Example Requests

Get all currencies:

```http
GET /currencies
```

Search by currency code:

```http
GET /currencies?search=USD
```

Search by currency name:

```http
GET /currencies?search=dollar
```

## Example Response

```json
{
  "EUR": {
    "name": "Euro",
    "symbol": "EUR",
    "numeric_code": "978",
    "currency_symbol": "€",
    "currency_symbol_narrow": null,
    "decimal_places": 2,
    "rounding": 0,
    "countries": ["AD", "AT", "AX", "BE", "BL", "CY", "DE", "EA", "EE", "ES", "FI", "FR", "GF", "GP", "GR", "HR", "IC", "IE", "IT", "LT", "LU", "LV", "MC", "ME", "MF", "MQ", "MT", "NL", "PM", "PT", "RE", "SI", "SK", "SM", "VA", "XK", "YT"],
    "official_countries": ["AD", "AT", "AX", "BE", "BL", "CY", "DE", "EA", "EE", "ES", "FI", "FR", "GF", "GP", "GR", "HR", "IC", "IE", "IT", "LT", "LU", "LV", "MC", "ME", "MF", "MQ", "MT", "NL", "PM", "PT", "RE", "SI", "SK", "SM", "VA", "XK", "YT"],
    "historical": false
  },
  "USD": {
    "name": "US Dollar",
    "symbol": "USD",
    "numeric_code": "840",
    "currency_symbol": "$",
    "currency_symbol_narrow": null,
    "decimal_places": 2,
    "rounding": 0,
    "countries": ["AS", "BQ", "DG", "EC", "FM", "GU", "HT", "IO", "MH", "MP", "PA", "PR", "PW", "SV", "TC", "TL", "UM", "US", "VG", "VI", "ZW"],
    "official_countries": ["AS", "BQ", "DG", "EC", "FM", "GU", "HT", "IO", "MH", "MP", "PA", "PR", "PW", "SV", "TC", "TL", "UM", "US", "VG", "VI", "ZW"],
    "historical": false
  },
  "GBP": {
    "name": "British Pound",
    "symbol": "GBP",
    "numeric_code": "826",
    "currency_symbol": "£",
    "currency_symbol_narrow": null,
    "decimal_places": 2,
    "rounding": 0,
    "countries": ["GB", "GG", "GS", "IM", "JE", "TA"],
    "official_countries": ["GB", "GG", "GS", "IM", "JE", "TA"],
    "historical": false
  }
}
```
