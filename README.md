# VATcomply

[![codecov](https://codecov.io/gh/madisvain/vatcomply/graph/badge.svg?token=ELA0NIP808)](https://codecov.io/gh/madisvain/vatcomply)
![tests](https://github.com/madisvain/vatcomply/actions/workflows/tests.yml/badge.svg)

[VATcomply](https://www.vatcomply.com) is a free API service providing:

- **VAT number validation** - Validate European VAT numbers using the official VIES database
- **Foreign exchange rates** - Daily rates from the European Central Bank with historical data
- **Visitor IP geolocation** - Automatic country detection from visitor's IP address
- **IBAN validation** - International Bank Account Number validation
- **Country & currency data** - Comprehensive country and currency information

**[Documentation](https://www.vatcomply.com)** | **[Interactive API Docs](https://api.vatcomply.com/docs)**

## Quick Start

Base URL: `https://api.vatcomply.com`

```shell
# Validate a VAT number
curl "https://api.vatcomply.com/vat?vat_number=BE0123456789"

# Get latest exchange rates
curl "https://api.vatcomply.com/rates"

# Get exchange rates with a specific base currency
curl "https://api.vatcomply.com/rates?base=USD&symbols=GBP,JPY"

# Validate an IBAN
curl "https://api.vatcomply.com/iban?iban=GB82WEST12345698765432"

# Geolocate visitor IP
curl "https://api.vatcomply.com/geolocate"
```

## Development

### Setup

```shell
# Install dependencies
make pip      # or: uv sync
```

### Database Setup

```shell
# Run migrations
make migrate  # or: uv run python manage.py migrate

# Load initial data
uv run python manage.py load_countries
uv run python manage.py load_rates --last-90-days
```

### Running the Server

```shell
make run      # or: DEBUG=True uv run python manage.py runbolt --dev
```

### Exchange rate updates

Rates are stored in the database and refreshed from the ECB (not fetched per request):

- **Boot**: `start.sh` loads recent rates on deploy (when migrations run).
- **Hourly shell loop**: `start.sh` runs `load_rates --last-90-days` every hour (covers single-container deploys such as Railway).
- **In-process scheduler** (optional): set `BACKGROUND_SCHEDULER=true` so APScheduler also loads rates (hourly + immediately on worker start).
- **docker-compose**: a dedicated `cron` service runs the same jobs via `crontab`.

`/ready` includes a **rates freshness** check (fails if the latest `Rate.date` is older than `RATES_MAX_AGE_DAYS`, default 4). Monitor `/ready` in production.

Optional query flag: `GET /rates?strict=true` requires an exact date (no weekend fallback) and returns **503** for stale latest data.

### Testing

```shell
# Run all tests
make test     # or: uv run pytest

# Run specific tests
uv run pytest vatcomply/tests/test_rates.py

# Test with coverage
make coverage # or: uv run coverage run -m pytest && uv run coverage report -m
```

## Contributing

Thanks for your interest in the project! All pull requests are welcome from developers of all skill levels. To get started, simply fork the master branch on GitHub to your personal account and then clone the fork into your development environment.

Madis Väin ([madisvain](https://github.com/madisvain) on Github) is the original creator of the VATcomply API.

## License

MIT
