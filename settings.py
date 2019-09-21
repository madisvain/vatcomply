from starlette.config import Config
from starlette.datastructures import CommaSeparatedStrings, URL

config = Config(".env")

DEBUG = config("DEBUG", cast=bool, default=False)
TESTING = config("TESTING", cast=bool, default=False)

DATABASE_URL = config("DATABASE_URL", cast=URL, default="sqlite:///db.sqlite3")

RATES_URL = config("RATES_URL", cast=URL, default="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml")
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

# Testing
if TESTING:
    pass
    # DATABASE_URL = DATABASE_URL.replace(path="/test_db.sqlite3")
