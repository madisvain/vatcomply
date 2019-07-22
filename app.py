import databases
import pendulum
import sqlalchemy
import uvicorn
import requests
import zeep

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from xml.etree import ElementTree

from pydantic import BaseModel, ValidationError, validator
from pydantic.dataclasses import dataclass
from starlette.applications import Starlette
from starlette.config import Config
from starlette.responses import UJSONResponse

config = Config(".env")
app = Starlette(debug=True)


# Database
metadata = sqlalchemy.MetaData()

Rates = sqlalchemy.Table(
    "rates",
    metadata,
    sqlalchemy.Column("date", sqlalchemy.Date, primary_key=True),
    sqlalchemy.Column("rates", sqlalchemy.JSON),
)

database = databases.Database(config("DATABASE_URL"))


@app.on_event("startup")
async def load_rates():
    await database.connect()

    # Load rates
    r = requests.get(config("HISTORIC_RATES_URL"))
    envelope = ElementTree.fromstring(r.content)

    namespaces = {
        "gesmes": "http://www.gesmes.org/xml/2002-08-01",
        "eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
    }
    data = envelope.findall("./eurofxref:Cube/eurofxref:Cube[@time]", namespaces)
    for i, d in enumerate(data):
        time = pendulum.parse(d.attrib["time"], strict=False)
        if not await database.fetch_one(query=Rates.select().where(Rates.c.date == time)):
            await database.execute(
                query=Rates.insert(),
                values={"date": time, "rates": {str(c.attrib["currency"]): float(c.attrib["rate"]) for c in list(d)}},
            )


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


class VATValidationModel(BaseModel):
    vat_number: str

    @validator("vat_number")
    def format_validation(cls, v):
        # TODO: implement Regex validators
        return v


class RatesQueryValidationModel(BaseModel):
    base: str = "EUR"
    date: Optional[date]
    symbols: Optional[list]

    @validator("base")
    def base_validation(cls, base):
        if base not in config("SYMBOLS"):
            raise ValueError(f"Base currency {base} is not supported.")
        return base

    @validator("symbols", pre=True, whole=True)
    def symbols_validation(cls, symbols):
        symbols = symbols.split(",")
        diff = list(set(symbols) - set(config("SYMBOLS")))
        if diff:
            raise ValueError(f"Symbols {', '.join(diff)} are not supported.")
        return symbols


@app.route("/api/vat")
async def vat(request):
    try:
        VATValidationModel(**request.query_params)
        client = zeep.Client(wsdl=config("VIES_URL"))
        response = zeep.helpers.serialize_object(client.service.checkVat(countryCode="BE", vatNumber="0878065378"))
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
        date = (
            pendulum.instance(datetime.fromordinal(query.date.toordinal())).date()
            if query.date
            else pendulum.now().date()
        )

        # Get the rates data
        rates = await database.fetch_val(
            query=Rates.select().where(date <= date).order_by(Rates.c.date.desc()).limit(1), column=Rates.c.rates
        )

        # Base re-calculation
        if query.base and query.base != "EUR":
            base_rate = Decimal(rates[query.base])
            rates = {currency: Decimal(rate) / base_rate for currency, rate in rates.items()}
            rates.update({"EUR": Decimal(1) / base_rate})

        # Symbols
        if query.symbols:
            for rate in list(rates):
                if rate not in query.symbols:
                    del rates[rate]

        return UJSONResponse({"date": date.to_date_string(), "base": query.base, "rates": rates})
    except ValidationError as e:
        return UJSONResponse(e.errors())
