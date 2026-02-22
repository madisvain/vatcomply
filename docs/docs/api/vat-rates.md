---
title: VAT Rates
description: "Get current EU VAT rates for all 27 member states, sourced from the official European Commission TEDB database. Includes standard, reduced, super-reduced, and parking rates."
icon: lucide/percent
---

# VAT Rates

Get current VAT rates for all EU member states from the official European Commission TEDB (Taxes in Europe Database).

## Endpoint

```http
GET https://api.vatcomply.com/vat_rates
```

## Parameters

| Parameter      | Type   | Required | Description                                      |
|---------------|--------|----------|--------------------------------------------------|
| `country_code` | string | No       | Filter by EU member state code (e.g. `DE`, `FR`) |

## Example Request

```http
GET https://api.vatcomply.com/vat_rates
```

## Example Response

```json
[
  {
    "country_code": "DE",
    "country_name": "Germany",
    "standard_rate": 19.0,
    "reduced_rates": [7.0],
    "super_reduced_rate": null,
    "parking_rate": null,
    "currency": "EUR",
    "member_state": true
  },
  {
    "country_code": "FR",
    "country_name": "France",
    "standard_rate": 20.0,
    "reduced_rates": [5.5, 10.0],
    "super_reduced_rate": 2.1,
    "parking_rate": null,
    "currency": "EUR",
    "member_state": true
  }
]
```

## Response Fields

| Field                | Type          | Description                                    |
|---------------------|---------------|------------------------------------------------|
| `country_code`       | string        | 2-letter EU member state code                  |
| `country_name`       | string        | Full country name                              |
| `standard_rate`      | number        | Standard VAT rate (%)                          |
| `reduced_rates`      | array[number] | List of reduced VAT rates (%)                  |
| `super_reduced_rate` | number\|null  | Super-reduced rate, if applicable              |
| `parking_rate`       | number\|null  | Parking rate, if applicable                    |
| `currency`           | string        | Country currency code                          |
| `member_state`       | boolean       | Always `true` (EU member state)                |

## Filter by Country

```http
GET https://api.vatcomply.com/vat_rates?country_code=DE
```

The `country_code` parameter is case-insensitive.

```http
GET https://api.vatcomply.com/vat_rates?country_code=de
```

## Member State Codes

| Code | Country         | Code | Country        |
|------|----------------|------|----------------|
| AT   | Austria        | IE   | Ireland        |
| BE   | Belgium        | IT   | Italy          |
| BG   | Bulgaria       | LT   | Lithuania      |
| CY   | Cyprus         | LU   | Luxembourg     |
| CZ   | Czech Republic | LV   | Latvia         |
| DE   | Germany        | MT   | Malta          |
| DK   | Denmark        | NL   | Netherlands    |
| EE   | Estonia        | PL   | Poland         |
| EL   | Greece         | PT   | Portugal       |
| ES   | Spain          | RO   | Romania        |
| FI   | Finland        | SE   | Sweden         |
| FR   | France         | SI   | Slovenia       |
| HR   | Croatia        | SK   | Slovakia       |
| HU   | Hungary        |      |                |

!!! note "Greece uses EL"

    The TEDB service uses `EL` for Greece (not `GR`), following the EU convention. The `/vat_rates` endpoint preserves this code.

## Data Source

VAT rates are sourced from the European Commission's **TEDB** (Taxes in Europe Database) SOAP service and refreshed daily.
