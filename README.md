# VATcomply

[VATcomply](https://www.vatcomply.com) is a free API service for vat number validation, user ip geolocation and foreign exchange rates [published by the European Central Bank](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html).

## Usage

#### Lates & specific date rates

Get the latest foreign exchange rates.

```http
GET /rates
```

Rates are quoted against the Euro by default. Quote against a different currency by setting the base parameter in your request.

```http
GET /rates?base=USD
```

Request specific exchange rates by setting the symbols parameter.

```http
GET /rates?symbols=USD,GBP
```

#### Rates history and query parameters combinations

Get historical rates for a date

```http
GET /rates?date=2018-01-01
```

Limit results to specific exchange rates to save bandwidth with the symbols parameter.

```http
GET /rates?date=2018-01-01&symbols=ILS,JPY
```

Quote the historical rates against a different currency.

```http
GET /rates?date=2018-01-01&base=USD
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

## Stack

VATcomply API is built upon [Django](https://www.djangoproject.com/) with asyncronous views, [Pydantic](https://docs.pydantic.dev/latest/) and asyncronous ORM queries to achieve high throughput. The current setup can asyncronously handle thousands of requests per second.

#### Libraries used

- [Django](https://www.djangoproject.com/)
- [Pydantic](https://docs.pydantic.dev/latest/)
- [APScheduler](https://github.com/agronholm/apscheduler)
- [ultraJSON](https://github.com/esnme/ultrajson)

## Deployment

#### Virtualenv

```shell
pyenv shell 3.x.x
```

#### Install packages

```shell
virtualenv env
. env/bin/activate
pip install -r requirements.in --upgrade
```

#### Load in initial data & Scheduler

The scheduler will keep your database up to date hourly with information from European Central bank. It will download the last 90 days worth of data every hour.

_The reference rates are usually updated around 16:00 CET on every working day, except on TARGET closing days. They are based on a regular daily concertation procedure between central banks across Europe, which normally takes place at 14:15 CET._

On initialization it will check the database. If it's empty all the historic rates will be downloaded and records created in the database.

## Development

```shell
export DEBUG=True; uvicorn vatcomply.asgi:application --reload
```

or for simplicity a Makefile is provided with all the commands for development.

```shell
make run
```

## Migrations

Make migrations

```shell
make migrations
```

Run migrations

```shell
make migrate
```

## Tests

```shell
make test
```

## Contributing

Thanks for your interest in the project! All pull requests are welcome from developers of all skill levels. To get started, simply fork the master branch on GitHub to your personal account and then clone the fork into your development environment.

Madis Väin ([madisvain](https://github.com/madisvain) on Github) is the original creator of the VATcomply API.

## License

MIT
