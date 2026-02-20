---
title: Rate Limiting & Usage
description: Rate limits and HTTP status codes for the VATcomply API
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
