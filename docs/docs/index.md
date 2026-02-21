---
title: VATcomply - Free VAT Validation & Exchange Rates API
description: Free API service for VAT number validation, foreign exchange rates, IP geolocation, and IBAN validation
icon: lucide/home
---

# VATcomply

[VATcomply](https://www.vatcomply.com) is a free API service providing:

- **VAT number validation** - Validate European VAT numbers using the official VIES database
- **Foreign exchange rates** - Daily rates from the European Central Bank with historical data
- **Visitor IP geolocation** - Automatic country detection from visitor's IP address
- **IBAN validation** - International Bank Account Number validation
- **Country & currency data** - Comprehensive country and currency information

[Interactive API Documentation](https://api.vatcomply.com/docs){ .md-button .md-button--primary } [View on GitHub](https://github.com/madisvain/vatcomply){ .md-button }

## Quick Start

All endpoints are available at `https://api.vatcomply.com` with no authentication required.

```http
GET https://api.vatcomply.com/rates
GET https://api.vatcomply.com/vat?vat_number=BE0123456789
GET https://api.vatcomply.com/geolocate
GET https://api.vatcomply.com/iban?iban=GB82WEST12345698765432
GET https://api.vatcomply.com/countries
GET https://api.vatcomply.com/currencies
```

## Base URL

```
https://api.vatcomply.com
```

No API key or authentication is needed. Rate limits are applied per IP address at **2 requests per second**.
