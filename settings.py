from databases import DatabaseURL
from starlette.config import Config
from starlette.datastructures import CommaSeparatedStrings, URL

config = Config(".env")

DEBUG = config("DEBUG", cast=bool, default=False)
TESTING = config("TESTING", cast=bool, default=False)

DATABASE_URL = config("DATABASE_URL", cast=DatabaseURL, default="sqlite:///db.sqlite3")
TEST_DATABASE_URL = DATABASE_URL.replace(database="test_" + DATABASE_URL.database)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=CommaSeparatedStrings, default=[])
FORCE_HTTPS = config("FORCE_HTTPS", cast=bool, default=False)

RATES_URL = config("RATES_URL", cast=URL, default="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml")
RATES_LAST_90_DAYS_URL = config(
    "RATES_LAST_90_DAYS_URL", cast=URL, default="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
)
VIES_URL = config("VIES_URL", cast=URL, default="http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl")

SYMBOLS = config(
    "SYMBOLS",
    cast=CommaSeparatedStrings,
    default=[
        "EUR",
        "USD",
        "JPY",
        "BGN",
        "CZK",
        "DKK",
        "GBP",
        "HUF",
        "PLN",
        "RON",
        "SEK",
        "CHF",
        "ISK",
        "NOK",
        "HRK",
        "RUB",
        "TRY",
        "AUD",
        "BRL",
        "CAD",
        "CNY",
        "HKD",
        "IDR",
        "ILS",
        "INR",
        "KRW",
        "MXN",
        "MYR",
        "NZD",
        "PHP",
        "SGD",
        "THB",
        "ZAR",
    ],
)

SENTRY_DSN = config("SENTRY_DSN", cast=str, default="")

# Testing
if TESTING:
    pass
    # DATABASE_URL = DATABASE_URL.replace(path="/test_db.sqlite3")
