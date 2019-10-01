import pendulum
import sentry_sdk
import uvicorn
import zeep

from babel.numbers import get_currency_name, get_currency_symbol
from datetime import datetime
from decimal import Decimal
from pydantic import ValidationError
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import UJSONResponse

from db import database, Rates
from models import VATValidationModel, RatesQueryValidationModel
from settings import ALLOWED_HOSTS, DEBUG, FORCE_HTTPS, SENTRY_DSN, SYMBOLS, TESTING, VIES_URL


app = Starlette(debug=DEBUG)

""" Allowed hosts """
if ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(ALLOWED_HOSTS))

""" Force HTTPS """
if FORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)

""" Sentry """
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN)
    app.add_middleware(SentryAsgiMiddleware)


""" Startup & Shutdown """


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


""" API """


@app.route("/api/vat")
async def vat(request):
    try:
        query = VATValidationModel(**request.query_params)
        print(query.vat_number[:2])
        print(query.vat_number[2:])
        client = zeep.Client(wsdl=str(VIES_URL))
        try:
            response = zeep.helpers.serialize_object(
                client.service.checkVat(countryCode=query.vat_number[:2], vatNumber=query.vat_number[2:])
            )
        except zeep.exceptions.Fault as e:
            return UJSONResponse({"error": e.message})

        return UJSONResponse({k: response[k] for k in ("name", "address", "valid")})
    except ValidationError as e:
        return UJSONResponse(e.errors())


@app.route("/api/countries")
async def countries(request):
    return UJSONResponse({})


@app.route("/api/rates")
async def rates(request):
    try:
        query = RatesQueryValidationModel(**request.query_params)

        # Find the date
        date = query.date if query.date else pendulum.now().date()

        # Get the rates data
        record = await database.fetch_one(
            query=Rates.select().where(Rates.c.date <= date).order_by(Rates.c.date.desc()).limit(1)
        )

        # Base re-calculation
        rates = record.rates
        if query.base and query.base != "EUR":
            base_rate = Decimal(record.rates[query.base])
            rates = {currency: Decimal(rate) / base_rate for currency, rate in rates.items()}
            rates.update({"EUR": Decimal(1) / base_rate})

        # Symbols
        if query.symbols:
            for rate in list(rates):
                if rate not in query.symbols:
                    del rates[rate]

        return UJSONResponse({"date": record.date.isoformat(), "base": query.base, "rates": rates})
    except ValidationError as e:
        return UJSONResponse(e.errors(), status_code=400)


@app.route("/api/currencies")
async def currencies(request):
    currencies = {}
    for symbol in list(SYMBOLS):
        currencies[symbol] = {
            "name": get_currency_name(symbol, locale="en"),
            "symbol": get_currency_symbol(symbol, locale="en"),
        }
    return UJSONResponse(currencies)
