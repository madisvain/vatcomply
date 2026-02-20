---
title: Foreign Exchange Rates
description: Daily foreign exchange rates from the European Central Bank with historical data
---

# Foreign Exchange Rates

Get daily foreign exchange rates from the European Central Bank, including historical data.

## Latest Rates

```http
GET /rates
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
| `rates` | object | Map of currency codes to exchange rate values   |

## Base Currency Conversion

Return rates relative to a specific base currency.

```http
GET /rates?base=USD
```

## Specific Currencies

Filter the response to only include specific currencies.

```http
GET /rates?symbols=USD,GBP
```

## Historical Rates

Retrieve rates for a specific date.

```http
GET /rates?date=2018-01-01
```

## Combined Parameters

All parameters can be combined in a single request.

```http
GET /rates?date=2018-01-01&symbols=USD,GBP&base=EUR
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
