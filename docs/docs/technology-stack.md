---
title: Technology Stack
description: Technologies powering the VATcomply API
---

# Technology Stack

VATcomply API is built on Python with the following key technologies:

| Technology | Description |
|-----------|-------------|
| [Django](https://www.djangoproject.com/) | Core web framework with async views |
| [Django Bolt](https://github.com/andrewgodwin/django-bolt) | REST API framework |
| [msgspec](https://jcristharif.com/msgspec/) | High-performance serialization and validation |
| [APScheduler](https://github.com/agronholm/apscheduler) | Background task scheduler |
| [Httpx](https://www.python-httpx.org/) | Async HTTP client |
| [Uvicorn](https://www.uvicorn.org/) | ASGI server |

This stack enables the API to handle thousands of requests per second asynchronously.
