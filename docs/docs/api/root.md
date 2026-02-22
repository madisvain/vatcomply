---
title: API Root
description: "VATcomply VAT compliance API root endpoint. Returns service status, version, and links to all endpoints — VAT validation, exchange rates, geolocation, and IBAN."
icon: lucide/route
---

# API Root

Returns general information about the API, its status, and available endpoints.

## Endpoint

```http
GET https://api.vatcomply.com/
```

## Parameters

No parameters required.

## Response Fields

| Field           | Type   | Description                              |
|-----------------|--------|------------------------------------------|
| `name`          | string | API name                                 |
| `version`       | string | API version                              |
| `status`        | string | Current API status                       |
| `description`   | string | Brief description of the API             |
| `documentation` | string | URL to the API documentation             |
| `endpoints`     | object | Map of endpoint names to their URLs      |
| `contact`       | string | Support contact email                    |

## Example Response

```json
{
  "name": "VATComply API",
  "version": "1.0.0",
  "status": "operational",
  "description": "VAT validation API, geolocation tools, and ECB exchange rates",
  "documentation": "https://www.vatcomply.com/docs",
  "endpoints": {
    "countries": "https://api.vatcomply.com/countries",
    "currencies": "https://api.vatcomply.com/currencies",
    "geolocate": "https://api.vatcomply.com/geolocate",
    "iban": "https://api.vatcomply.com/iban",
    "vat": "https://api.vatcomply.com/vat",
    "rates": "https://api.vatcomply.com/rates"
  },
  "contact": "support@vatcomply.com"
}
```
