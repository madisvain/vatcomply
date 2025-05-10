# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VATcomply is a free API service that provides:
- VAT number validation
- User IP geolocation
- Foreign exchange rates from the European Central Bank

The project consists of a Django backend API service and a Next.js frontend website.

## Technology Stack

### Backend
- **Django**: Core web framework with async views and ORM
- **Django Ninja**: REST API framework built on top of Django
- **Pydantic**: Data validation
- **APScheduler**: Background task scheduler for fetching currency rates
- **Httpx**: Async HTTP client for external API calls
- **Uvicorn**: ASGI server

### Frontend
- **Next.js**: React-based frontend framework
- **SCSS**: For styling components

## Key Commands

### Setup & Installation

```shell
# Set up Python environment
pyenv shell 3.11.x
virtualenv env
. env/bin/activate

# Install dependencies
make pip      # or: uv pip install -r requirements.in --upgrade
make freeze   # or: uv pip compile requirements.in -o requirements.txt
```

### Development

```shell
# Run development server
make run      # or: export DEBUG=True; uvicorn vatcomply.asgi:application --reload

# Database migrations
make migrations  # Create new migrations
make migrate     # Apply migrations

# Data loading
python manage.py load_countries  # Load country data
python manage.py load_rates      # Load exchange rates (historical)
python manage.py load_rates --last-90-days  # Load last 90 days of rates
```

### Testing

```shell
# Run all tests
make test     # or: python manage.py test --keepdb

# Run specific test file or class
python manage.py test vatcomply.tests.test_rates  # Run tests in file
python manage.py test vatcomply.tests.test_rates.RatesTest  # Run specific test class

# Test with coverage report
make coverage  # or: coverage run manage.py test --keepdb && coverage report -m
```

## Project Architecture

### Core Components

1. **API Endpoints** (`vatcomply/api.py`)
   - `/rates`: Foreign exchange rates from ECB
   - `/vat`: VAT number validation
   - `/countries`: List of countries and their details
   - `/currencies`: Supported currency information
   - `/geolocate`: IP-based geolocation
   - `/iban`: IBAN validation

2. **Data Models** (`vatcomply/models.py`)
   - `Rate`: Exchange rate data by date
   - `Country`: Country information and metadata

3. **Schemas** (`vatcomply/schemas.py`)
   - Pydantic models for request/response validation

4. **Background Tasks** (`vatcomply/middleware.py`)
   - `BackgroundTasksMiddleware`: ASGI middleware that runs periodic tasks
   - Scheduler that fetches currency rates from ECB

5. **Management Commands** (`vatcomply/management/commands/`)
   - `load_countries.py`: Imports country data 
   - `load_rates.py`: Imports exchange rates from ECB

### Data Flow

1. Exchange rate data:
   - Fetched from ECB XML endpoints
   - Stored in the `Rate` model with date as primary key
   - Updated hourly by the background scheduler
   - Served through the `/rates` API endpoint with options for base currency, symbols, and dates

2. Country data:
   - Imported from JSON source
   - Stored in the `Country` model
   - Used for VAT validation and geolocation features

## Environment Variables

Key environment variables used:
- `DEBUG`: Enable debug mode (default: False)
- `SECRET_KEY`: Django secret key
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `BACKGROUND_SCHEDULER`: Enable background scheduler (default: False)
- `THROTTLE`: Enable request throttling (default: True)
- `BASE_URL`: Base URL for the application (default: "http://localhost:8000")