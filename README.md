# VATcomply

[![codecov](https://codecov.io/gh/madisvain/vatcomply/graph/badge.svg?token=ELA0NIP808)](https://codecov.io/gh/madisvain/vatcomply)
![tests](https://github.com/madisvain/vatcomply/actions/workflows/tests.yml/badge.svg)

[VATcomply](https://www.vatcomply.com) is a free API service providing:

- **VAT number validation** - Validate European VAT numbers using the official VIES database
- **Foreign exchange rates** - Daily rates from the European Central Bank with historical data
- **Visitor IP geolocation** - Automatic country detection from visitor's IP address
- **IBAN validation** - International Bank Account Number validation
- **Country & currency data** - Comprehensive country and currency information

**📖 [Interactive API Documentation](https://api.vatcomply.com/docs)** - Complete Swagger/OpenAPI schema with live testing

## API Documentation

### VAT Number Validation

Validate European VAT numbers using the official VIES (VAT Information Exchange System) database.

```http
GET /vat?vat_number=BE0123456789
```

**Response:**
```json
{
  "valid": true,
  "vat_number": "123456789",
  "name": "COMPANY NAME",
  "address": "COMPANY ADDRESS",
  "country_code": "BE"
}
```

**Supported countries:** All EU member states plus Northern Ireland (XI prefix)

**Note:** UK (GB) VAT numbers are no longer supported since Brexit (01/01/2021). Use XI prefix for Northern Ireland businesses.

### Foreign Exchange Rates

#### Latest rates

Get the latest foreign exchange rates.

```http
GET /rates
```

**Response:**
```json
{
  "date": "2024-01-15",
  "base": "EUR",
  "rates": {
    "USD": 1.0856,
    "GBP": 0.8642,
    "JPY": 156.92
  }
}
```

#### Base currency conversion

Rates are quoted against the Euro by default. Quote against a different currency by setting the base parameter.

```http
GET /rates?base=USD
```

#### Specific currencies

Request specific exchange rates by setting the symbols parameter.

```http
GET /rates?symbols=USD,GBP
```

#### Historical rates

Get historical rates for a specific date.

```http
GET /rates?date=2018-01-01
```

#### Combined parameters

Combine parameters for precise data retrieval.

```http
GET /rates?date=2018-01-01&symbols=USD,GBP&base=EUR
```

#### Client side usage

The primary use case is client side. For instance, with [money.js](https://openexchangerates.github.io/money.js/) in the browser

```js
let demo = () => {
  let rate = fx(1).from("GBP").to("USD");
  alert("£1 = $" + rate.toFixed(4));
};

fetch("https://api.vatcomply.com/rates")
  .then((resp) => resp.json())
  .then((data) => (fx.rates = data.rates))
  .then(demo);
```

### Visitor IP Geolocation

Get country information for the visitor's IP address automatically.

```http
GET /geolocate
```

**Response:**
```json
{
  "iso2": "US",
  "iso3": "USA",
  "country_code": "US",
  "name": "United States",
  "numeric_code": 840,
  "phone_code": "+1",
  "capital": "Washington",
  "currency": "USD",
  "tld": ".us",
  "region": "Americas",
  "subregion": "Northern America",
  "latitude": 39.76,
  "longitude": -98.5,
  "emoji": "🇺🇸",
  "ip": "192.168.1.1"
}
```

**Note:** This endpoint uses CloudFlare headers to detect the visitor's country. Custom IP addresses are not supported.

### IBAN Validation

Validate International Bank Account Numbers (IBAN).

```http
GET /iban?iban=GB82WEST12345698765432
```

**Response:**
```json
{
  "valid": true,
  "iban": "GB82WEST12345698765432",
  "bank_name": "Westpac Banking Corporation",
  "bic": "WESTGB2L",
  "country_code": "GB",
  "country_name": "United Kingdom",
  "checksum_digits": "82",
  "bank_code": "WEST",
  "branch_code": "123456",
  "account_number": "98765432",
  "bban": "WEST12345698765432",
  "in_sepa_zone": false
}
```

### Countries

Get a list of all countries with detailed information.

```http
GET /countries
```

**Response:**
```json
[
  {
    "iso2": "AD",
    "iso3": "AND",
    "name": "Andorra",
    "numeric_code": 20,
    "phone_code": "+376",
    "capital": "Andorra la Vella",
    "currency": "EUR",
    "tld": ".ad",
    "region": "Europe",
    "subregion": "Southern Europe",
    "latitude": 42.5,
    "longitude": 1.5,
    "emoji": "🇦🇩"
  }
]
```

### Currencies

Get information about all supported currencies.

```http
GET /currencies
```

**Response:**
```json
{
  "USD": {
    "name": "United States Dollar",
    "symbol": "USD"
  },
  "EUR": {
    "name": "Euro",
    "symbol": "EUR"
  }
}
```

## Rate Limiting

The API includes built-in rate limiting to ensure fair usage:

- **Anonymous requests:** 2 requests per second
- No authentication required
- Rate limits are applied per IP address

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (invalid country code, etc.)
- `422` - Validation Error (malformed data)
- `429` - Too Many Requests (rate limit exceeded)

**Error Response Format:**
```json
{
  "error": "Error message description"
}
```

## Stack

VATcomply API is built on Python with key technologies including:

- [Django](https://www.djangoproject.com/): The core web framework, utilizing asynchronous views and ORM queries for high throughput.
- [Django Ninja](https://django-ninja.rest-framework.com/): Powers the REST API development on top of Django.
- [Pydantic](https://docs.pydantic.dev/latest/): Used for robust data validation.
- [APScheduler](https://github.com/agronholm/apscheduler): Manages scheduled tasks, like fetching updated exchange rates.
- [Httpx](https://www.python-httpx.org/): An asynchronous HTTP client for making external API calls (e.g., to the European Central Bank).
- [Uvicorn](https://www.uvicorn.org/): ASGI servers for running the application.

This stack enables the API to handle thousands of requests per second asynchronously.

## Development

### Setup

```shell
# Set up Python environment
pyenv shell 3.11.x
virtualenv env
. env/bin/activate

# Install dependencies
make pip      # or: uv pip install -r requirements.in --upgrade
make freeze   # or: uv pip compile requirements.in -o requirements.txt
```

### Database Setup

```shell
# Run migrations
make migrate     # or: python manage.py migrate

# Load initial data
python manage.py load_countries  # Load country data
python manage.py load_rates      # Load exchange rates (historical)
python manage.py load_rates --last-90-days  # Load last 90 days only
```

### Running the Server

```shell
# Development server
make run      # or: export DEBUG=True; uvicorn vatcomply.asgi:application --reload
```

### Background Scheduler

The scheduler keeps exchange rates updated hourly from the European Central Bank:

- Downloads the last 90 days of data every hour
- Rates are updated around 16:00 CET on working days
- Based on daily concertation between European central banks at 14:15 CET
- On first run, downloads all historical rates if database is empty

### Database Migrations

```shell
# Create new migrations
make migrations  # or: python manage.py makemigrations

# Apply migrations
make migrate     # or: python manage.py migrate
```

### Testing

```shell
# Run all tests
make test        # or: python manage.py test --keepdb

# Run specific tests
python manage.py test vatcomply.tests.test_rates
python manage.py test vatcomply.tests.test_rates.RatesTest

# Test with coverage
make coverage    # or: coverage run manage.py test --keepdb && coverage report -m
```

## Contributing

Thanks for your interest in the project! All pull requests are welcome from developers of all skill levels. To get started, simply fork the master branch on GitHub to your personal account and then clone the fork into your development environment.

Madis Väin ([madisvain](https://github.com/madisvain) on Github) is the original creator of the VATcomply API.

## License

MIT
