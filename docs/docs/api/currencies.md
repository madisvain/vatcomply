---
title: Currencies
description: Information about all supported currencies
---

# Currencies

Retrieve information about all supported currencies.

## Endpoint

```http
GET /currencies
```

## Parameters

No parameters required. Returns all available currencies.

## Response Fields

The response is a JSON object keyed by currency code. Each value contains:

| Field    | Type   | Description               |
|----------|--------|---------------------------|
| `name`   | string | Full currency name        |
| `symbol` | string | Currency code (e.g. `EUR`)|

## Example Response

```json
{
  "EUR": {
    "name": "Euro",
    "symbol": "EUR"
  },
  "USD": {
    "name": "US Dollar",
    "symbol": "USD"
  },
  "GBP": {
    "name": "British Pound",
    "symbol": "GBP"
  }
}
```
