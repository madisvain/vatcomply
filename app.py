import fcntl
import pendulum
import sentry_sdk
import ujson
import uvicorn
import zeep

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from babel.numbers import get_currency_name, get_currency_symbol
from datetime import datetime
from decimal import Decimal
from passlib.hash import pbkdf2_sha256
from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.applications import Starlette
from starlette.authentication import requires
from starlette.background import BackgroundTask
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from typing import Any

from auth import TokenAuthenticationBackend
from db import database, Rates, Users
from errors import AlreadyExistsError
from models import LoginValidationModel, RatesQueryValidationModel, RegistrationValidationModel, VATValidationModel
from settings import ALLOWED_HOSTS, CORS, DEBUG, FORCE_HTTPS, SENTRY_DSN, SYMBOLS, TESTING, VIES_URL
from utils import load_rates


class UJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return ujson.dumps(content)


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
    return UJSONResponse({"country_code": country_code.upper() if country_code else None, "ip": ip})


@app.route("/countries")
# @requires("authenticated")
async def countries(request):
    return UJSONResponse({})


@app.route("/rates")
# @requires("authenticated")
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
    return UJSONResponse(currencies)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
