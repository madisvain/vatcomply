---
title: IP Geolocation
description: Automatic country detection from visitor's IP address
icon: lucide/map-pin
---

# Visitor IP Geolocation

Automatic country detection from the visitor's IP address using CDN headers ([Cloudflare](https://www.cloudflare.com/) or [Bunny.net](https://bunny.net/)).

!!! info "CDN Requirement"

    This endpoint relies on CDN-provided headers (`CF-IPCountry` from [Cloudflare](https://www.cloudflare.com/) or `Cdn-RequestCountryCode` from [Bunny.net](https://bunny.net/)) to determine the visitor's country. It will not work without a supported CDN in front of the API.

## Endpoint

```http
GET /geolocate
```

## Parameters

No parameters required. The visitor's country and IP address are detected automatically from CDN headers.

## Response Fields

| Field          | Type        | Description                          |
|----------------|-------------|--------------------------------------|
| `iso2`         | string      | ISO 3166-1 alpha-2 country code      |
| `iso3`         | string      | ISO 3166-1 alpha-3 country code      |
| `country_code` | string      | Country code (same as `iso2`)        |
| `name`         | string      | Country name                         |
| `numeric_code` | integer     | ISO 3166-1 numeric code              |
| `phone_code`   | string      | International dialing code           |
| `capital`      | string      | Capital city                         |
| `currency`     | string      | Currency code                        |
| `tld`          | string      | Top-level domain                     |
| `region`       | string      | Geographic region                    |
| `subregion`    | string      | Geographic subregion                 |
| `latitude`     | number      | Latitude coordinate                  |
| `longitude`    | number      | Longitude coordinate                 |
| `emoji`        | string      | Country flag emoji                   |
| `ip`           | string/null | Visitor's IP address (Cloudflare only) |

## Example Response

```json
{
  "iso2": "US",
  "iso3": "USA",
  "country_code": "US",
  "name": "United States",
  "numeric_code": 840,
  "phone_code": "1",
  "capital": "Washington",
  "currency": "USD",
  "tld": ".us",
  "region": "Americas",
  "subregion": "Northern America",
  "latitude": 38.0,
  "longitude": -97.0,
  "emoji": "🇺🇸",
  "ip": "203.0.113.1"
}
```

## Error Responses

**404 - No CDN headers detected:**

```json
{
  "error": "Country code not received from CDN headers (CF-IPCountry or Cdn-RequestCountryCode)."
}
```

**404 - Country not found:**

```json
{
  "error": "Data for country code `XX` not found."
}
```
