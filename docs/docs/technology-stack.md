---
title: Technology Stack
description: Technologies powering the VATcomply API
icon: lucide/layers
---

# Technology Stack

VATcomply API is built on Python with the following key technologies:

| Technology | Description |
|-----------|-------------|
| [Django](https://www.djangoproject.com/) | Core web framework with async views |
| [Django Bolt](https://github.com/dj-bolt/django-bolt) | High-performance API framework with built-in Rust-powered server |
| [msgspec](https://jcristharif.com/msgspec/) | High-performance serialization and validation |
| [Httpx](https://www.python-httpx.org/) | Async HTTP client for external API calls |
| [Zeep](https://docs.python-zeep.org/) | SOAP client for VIES VAT validation |
| [Schwifty](https://github.com/mdomke/schwifty) | IBAN/BIC validation |
| [lxml](https://lxml.de/) | XML parsing for ECB exchange rate data |
| [Pendulum](https://pendulum.eustace.io/) | Date/time handling |
| [Sentry](https://sentry.io/) | Error monitoring and tracking |

This stack enables the API to handle thousands of requests per second asynchronously.

## Django Bolt

[Django Bolt](https://bolt.farhana.li/) is a high-performance API framework that combines Django's familiar patterns with Rust-powered speed. It uses decorator-based routing with automatic request validation through Python type hints and [msgspec](https://jcristharif.com/msgspec/) for serialization.

Key advantages for VATcomply:

- **Async-first** - Native async/await support for non-blocking I/O, used throughout for external API calls (VIES, ECB)
- **Full Django integration** - Works seamlessly with Django ORM, authentication, middleware, and admin
- **Automatic API docs** - Generates interactive documentation at [`/docs`](https://api.vatcomply.com/docs) with Swagger/OpenAPI
- **Type-safe validation** - Request parameters are validated automatically via type hints, reducing boilerplate
