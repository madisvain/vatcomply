import fcntl
import pendulum
import sentry_sdk
import ujson
import uvicorn
import zeep

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from babel.numbers import get_currency_name, get_currency_symbol
from decimal import Decimal
from passlib.hash import pbkdf2_sha256
from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.applications import Starlette
from starlette.authentication import requires
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from typing import Any

from auth import TokenAuthenticationBackend
from db import database, Countries, Rates, Users
from errors import AlreadyExistsError
from models import (
    LoginValidationModel,
    RatesQueryValidationModel,
    RegistrationValidationModel,
    VATValidationModel,
    VatRatesModel,
)
from settings import ALLOWED_HOSTS, CORS, DEBUG, FORCE_HTTPS, SENTRY_DSN, SYMBOLS, TESTING, VIES_URL
from utils import load_countries, load_rates


class UJSONResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        assert ujson is not None, "ujson must be installed to use UJSONResponse"
        return ujson.dumps(content, ensure_ascii=False).encode("utf-8")


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

""" CORS """
if CORS:
    app.add_middleware(CORSMiddleware, allow_origins=["*"])

""" Authentication """
app.add_middleware(AuthenticationMiddleware, backend=TokenAuthenticationBackend())


""" Startup & Shutdown """


@app.on_event("startup")
async def startup():
    await database.connect()

    # Schedule exchangerate updates
    try:
        _ = open("scheduler.lock", "w")
        fcntl.lockf(_.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        scheduler = AsyncIOScheduler()
        scheduler.start()

        if not TESTING:
            # Updates lates 90 days data
            scheduler.add_job(load_rates, "interval", hours=1, minutes=10)

            # Fill up database with rates
            scheduler.add_job(load_rates, kwargs={"last_90_days": False})

            # Countries
            scheduler.add_job(load_countries)
    except BlockingIOError:
        pass


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


""" API """


@app.route("/login", methods=["POST"])
async def login(request):
    try:
        data = await request.json()
        login = LoginValidationModel(**data)

        return UJSONResponse(login.dict())
    except ValidationError as e:
        return UJSONResponse(e.errors(), status_code=400)


@app.route("/register", methods=["POST"])
async def register(request):
    try:
        data = await request.json()
        registration = RegistrationValidationModel(**data)

        # Check if the email is unique
        user = await database.fetch_one(query=Users.select().where(Users.c.email == registration.email))
        if user:
            raise ValidationError(
                [ErrorWrapper(AlreadyExistsError(email=registration.email), loc="email")],
                model=RegistrationValidationModel,
            )

        await database.execute(
            query=Users.insert(),
            values={
                "email": registration.email,
                "password": pbkdf2_sha256.hash(registration.password.get_secret_value()),
            },
        )
        response = registration.dict()
        del response["password"]
        return UJSONResponse(response, status_code=201)
    except ValidationError as e:
        return UJSONResponse(e.errors(), status_code=400)


@app.route("/vat")
# @requires("authenticated")
async def vat(request):
    try:
        query = VATValidationModel(**request.query_params)
        client = zeep.Client(wsdl=str(VIES_URL))
        try:
            response = zeep.helpers.serialize_object(
                client.service.checkVat(countryCode=query.vat_number[:2], vatNumber=query.vat_number[2:])
            )
        except zeep.exceptions.Fault as e:
            return UJSONResponse({"error": e.message})

        return UJSONResponse(
            {
                "valid": response["valid"],
                "vat_number": response["vatNumber"],
                "name": response["name"],
                "address": response["address"].strip() if response["address"] else "",
                "country_code": response["countryCode"],
            }
        )
    except ValidationError as e:
        return UJSONResponse(e.errors(), status_code=400)


@app.route("/vat/rates")
# @requires("authenticated")
async def vat_rates(request):
    try:
        query = VATRatesModel(**request.query_params)
        client = zeep.Client(wsdl=str(VIES_URL))
        try:
            response = zeep.helpers.serialize_object(
                client.service.checkVat(countryCode=query.vat_number[:2], vatNumber=query.vat_number[2:])
            )
        except zeep.exceptions.Fault as e:
            return UJSONResponse({"error": e.message})

        return UJSONResponse(
            {
                "valid": response["valid"],
                "vat_number": response["vatNumber"],
                "name": response["name"],
                "address": response["address"].strip(),
                "country_code": response["countryCode"],
            }
        )
    except ValidationError as e:
        return UJSONResponse(e.errors(), status_code=400)


@app.route("/geolocate", methods=["GET", "HEAD"])
async def geolocate(request):
    country_code = request.headers.get("CF-IPCountry")
    ip = request.headers.get("CF-Connecting-IP")

    if not country_code:
        return UJSONResponse({"ip": ip}, status_code=404)

    # Get the rates data
    record = await database.fetch_one(query=Countries.select().where(Countries.c.iso2 == country_code.upper()))

    return UJSONResponse(
        {
            "iso2": record.iso2 if record else None,
            "iso3": record.iso3 if record else None,
            "country_code": country_code.upper() if country_code else None,
            "name": record.name if record else None,
            "numeric_code": record.numeric_code if record else None,
            "phone_code": record.phone_code if record else None,
            "capital": record.capital if record else None,
            "currency": record.currency if record else None,
            "tld": record.tld if record else None,
            "region": record.region if record else None,
            "subregion": record.subregion if record else None,
            "latitude": Decimal(record.latitude) if record else None,
            "longitude": Decimal(record.longitude) if record else None,
            "emoji": record.emoji if record else None,
            "ip": ip,
        }
    )


@app.route("/countries")
# @requires("authenticated")
async def countries(request):
    records = await database.fetch_all(query=Countries.select().order_by(Countries.c.iso2.asc()))

    countries = []
    for country in records:
        countries.append(
            {
                "iso2": country.iso2,
                "iso3": country.iso3,
                "name": country.name,
                "numeric_code": country.numeric_code,
                "phone_code": country.phone_code,
                "capital": country.capital,
                "currency": country.currency,
                "tld": country.tld,
                "region": country.region,
                "subregion": country.subregion,
                "latitude": Decimal(country.latitude),
                "longitude": Decimal(country.longitude),
                "emoji": country.emoji,
            }
        )
    return UJSONResponse(countries)


@app.route("/rates")
@app.route("/rates/latest")
@app.route("/rates/{date}")
async def rates(request):
    query_params = dict(request.query_params)
    if "date" in request.path_params:
        query_params["date"] = request.path_params["date"]

    try:
        query = RatesQueryValidationModel(**query_params)

        # Find the date
        date = query.date if query.date else pendulum.now().date()

        # Get the rates data
        record = await database.fetch_one(
            query=Rates.select().where(Rates.c.date <= date).order_by(Rates.c.date.desc()).limit(1)
        )

        # Base re-calculation
        rates = {"EUR": 1}
        rates.update(record.rates)
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


@app.route("/currencies")
# @requires("authenticated")
async def currencies(request):
    currencies = {}
    for symbol in list(SYMBOLS):
        currencies[symbol] = {
            "name": get_currency_name(symbol, locale="en"),
            "symbol": get_currency_symbol(symbol, locale="en"),
        }
    return UJSONResponse(currencies, headers={"Cache-Control": "max-age=86400"})


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
