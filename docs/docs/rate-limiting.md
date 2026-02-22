---
title: Rate Limiting & Usage
description: "VATcomply VAT compliance API rate limits, HTTP status codes, and error formats. Free with no API key — anonymous requests limited to 2 per second per IP."
icon: lucide/gauge
---

# Rate Limiting & Usage

## Rate Limits

- **Anonymous requests:** 2 requests per second
- No authentication required
- Rate limits applied per IP address

## HTTP Status Codes

| Code  | Description       |
|-------|-------------------|
| `200` | Success           |
| `400` | Bad Request       |
| `404` | Not Found         |
| `422` | Validation Error  |
| `429` | Rate Limit Exceeded |

### Error Response Format

All error responses return a JSON object with an `error` field:

```json
{
  "error": "Description of what went wrong."
}
```

Validation errors (422) return a JSON object with field-specific error messages:

```json
{
  "field_name": ["Error message for this field."]
}
```
