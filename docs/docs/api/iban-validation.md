---
title: IBAN Validation
description: International Bank Account Number validation with detailed information
icon: lucide/landmark
---

# IBAN Validation

Validate International Bank Account Numbers with detailed information.

## Endpoint

```http
GET /iban?iban={iban}
```

## Parameters

| Parameter | Type   | Required | Description                    |
|-----------|--------|----------|--------------------------------|
| `iban`    | string | Yes      | The IBAN to validate           |

## Response Fields

| Field             | Type    | Description                                |
|-------------------|---------|--------------------------------------------|
| `valid`           | boolean | Whether the IBAN is valid                  |
| `iban`            | string  | The IBAN as provided                       |
| `bank_name`       | string  | Name of the bank                           |
| `bic`             | string  | Bank Identifier Code (SWIFT/BIC)           |
| `country_code`    | string  | ISO 3166-1 alpha-2 country code            |
| `country_name`    | string  | Full country name                          |
| `checksum_digits` | string  | IBAN check digits                          |
| `bank_code`       | string  | Bank code portion of the IBAN              |
| `branch_code`     | string  | Branch code portion of the IBAN            |
| `account_number`  | string  | Account number portion of the IBAN         |
| `bban`            | string  | Basic Bank Account Number (national format)|
| `in_sepa_zone`    | boolean | Whether the country is in the SEPA zone    |

## Example Request

```http
GET /iban?iban=GB82WEST12345698765432
```

## Example Response

```json
{
  "valid": true,
  "iban": "GB82WEST12345698765432",
  "bank_name": "WESTMINSTER BANK",
  "bic": "WESTGB2L",
  "country_code": "GB",
  "country_name": "United Kingdom",
  "checksum_digits": "82",
  "bank_code": "WEST",
  "branch_code": "123456",
  "account_number": "98765432",
  "bban": "WEST12345698765432",
  "in_sepa_zone": true
}
```

## Error Responses

**400 - Invalid IBAN:**

```json
{
  "error": "Invalid IBAN checksum digits."
}
```
