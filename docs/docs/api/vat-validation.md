---
title: VAT Number Validation
description: "Free VAT number validation API — check EU VAT numbers in real time against the official VIES database. Supports all 27 EU member states and Northern Ireland."
icon: lucide/file-check
---

# VAT Number Validation

Validate European VAT numbers using the official VIES (VAT Information Exchange System) database.

## Endpoint

```http
GET https://api.vatcomply.com/vat?vat_number={vat_number}
```

## Parameters

| Parameter    | Type   | Required | Description                        |
|-------------|--------|----------|------------------------------------|
| `vat_number` | string | Yes      | The VAT number to validate (e.g. `BE0123456789`) |

## Example Request

```http
GET https://api.vatcomply.com/vat?vat_number=BE0123456789
```

## Example Response

```json
{
  "valid": true,
  "vat_number": "123456789",
  "name": "COMPANY NAME",
  "address": "COMPANY ADDRESS",
  "country_code": "BE"
}
```

## Error Responses

**400 - Invalid VAT number format:**

```json
{
  "error": "Invalid VAT number format. Expected format: Two-letter country code followed by 8-12 digits or letters."
}
```

**400 - UK (GB) VAT number rejected (Brexit):**

```json
{
  "error": "As of 01/01/2021, the VoW service to validate UK (GB) VAT numbers ceased to exist while a new service to validate VAT numbers of businesses operating under the Protocol on Ireland and Northern Ireland appeared. These VAT numbers are starting with the \"XI\" prefix."
}
```

**400 - VIES service fault:**

```json
{
  "error": "{ MS_UNAVAILABLE | INVALID_INPUT | SERVICE_UNAVAILABLE | ... }"
}
```

## Supported Countries

All EU member states are supported, plus Northern Ireland using the `XI` prefix.

!!! warning "UK VAT Numbers"

    UK (GB) VAT numbers are no longer supported since Brexit (01/01/2021).
    Use the `XI` prefix for Northern Ireland businesses.

## Country Prefixes

| Prefix | Country         | Prefix | Country        |
|--------|----------------|--------|----------------|
| AT     | Austria        | IE     | Ireland        |
| BE     | Belgium        | IT     | Italy          |
| BG     | Bulgaria       | LT     | Lithuania      |
| CY     | Cyprus         | LU     | Luxembourg     |
| CZ     | Czech Republic | LV     | Latvia         |
| DE     | Germany        | MT     | Malta          |
| DK     | Denmark        | NL     | Netherlands    |
| EE     | Estonia        | PL     | Poland         |
| EL     | Greece         | PT     | Portugal       |
| ES     | Spain          | RO     | Romania        |
| FI     | Finland        | SE     | Sweden         |
| FR     | France         | SI     | Slovenia       |
| HR     | Croatia        | SK     | Slovakia       |
| HU     | Hungary        | XI     | Northern Ireland |
