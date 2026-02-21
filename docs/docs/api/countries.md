---
title: Countries
description: Complete list of countries with detailed information
icon: lucide/globe
---

# Countries

Retrieve a list of countries with detailed information. All parameters are optional; omitting them returns every country.

## Endpoint

```http
GET /countries
```

## Parameters

| Parameter   | Type   | Description                                                        |
|-------------|--------|--------------------------------------------------------------------|
| `search`    | string | Search by country name, ISO2, or ISO3 code (case-insensitive)     |
| `region`    | string | Filter by geographic region, e.g. `Europe` (case-insensitive)     |
| `subregion` | string | Filter by geographic subregion, e.g. `Northern Europe` (case-insensitive) |
| `currency`  | string | Filter by currency code, e.g. `EUR` (case-insensitive)            |

All filters are composable with AND logic.

## Example Requests

```http
GET /countries?search=Estonia
GET /countries?region=Europe
GET /countries?subregion=Northern Europe
GET /countries?currency=EUR
GET /countries?region=Europe&currency=EUR
```

## Response Fields

| Field          | Type    | Description                          |
|----------------|---------|--------------------------------------|
| `iso2`         | string  | ISO 3166-1 alpha-2 country code      |
| `iso3`         | string  | ISO 3166-1 alpha-3 country code      |
| `name`         | string  | Country name                         |
| `numeric_code` | integer | ISO 3166-1 numeric code              |
| `phone_code`   | string  | International dialing code           |
| `capital`      | string  | Capital city                         |
| `currency`     | string  | Currency code (e.g. `EUR`)           |
| `tld`          | string  | Top-level domain (e.g. `.ee`)        |
| `region`       | string  | Geographic region (e.g. `Europe`)    |
| `subregion`    | string  | Geographic subregion                 |
| `latitude`     | number  | Latitude coordinate                  |
| `longitude`    | number  | Longitude coordinate                 |
| `emoji`        | string  | Country flag emoji                   |

## Example Response

The response is a JSON array of country objects.

```json
[
  {
    "iso2": "EE",
    "iso3": "EST",
    "name": "Estonia",
    "numeric_code": 233,
    "phone_code": "372",
    "capital": "Tallinn",
    "currency": "EUR",
    "tld": ".ee",
    "region": "Europe",
    "subregion": "Northern Europe",
    "latitude": 59.0,
    "longitude": 26.0,
    "emoji": "\ud83c\uddea\ud83c\uddea"
  },
  {
    "iso2": "FI",
    "iso3": "FIN",
    "name": "Finland",
    "numeric_code": 246,
    "phone_code": "358",
    "capital": "Helsinki",
    "currency": "EUR",
    "tld": ".fi",
    "region": "Europe",
    "subregion": "Northern Europe",
    "latitude": 64.0,
    "longitude": 26.0,
    "emoji": "\ud83c\uddeb\ud83c\uddee"
  }
]
```
