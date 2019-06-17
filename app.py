import pendulum
import uvicorn
import redis
import requests
import zeep

from datetime import date
from decimal import Decimal
from typing import Optional
from xml.etree import ElementTree

from pydantic import BaseModel, ValidationError, validator
from pydantic.dataclasses import dataclass
from starlette.applications import Starlette
from starlette.responses import UJSONResponse

SYMBOLS = [
    "USD",
    "JPY",
    "BGN",
    "CZK",
    "DKK",
    "BGP",
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
]
HISTORIC_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
VIES_URL = "http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl"

app = Starlette(debug=True)


@app.on_event("startup")
def load_rates():
    db = redis.Redis(host="localhost", port=6379, db=0)

    r = requests.get(HISTORIC_RATES_URL)
    envelope = ElementTree.fromstring(r.content)

    namespaces = {
        "gesmes": "http://www.gesmes.org/xml/2002-08-01",
        "eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
    }
    data = envelope.findall("./eurofxref:Cube/eurofxref:Cube[@time]", namespaces)
    for i, d in enumerate(data):
        time = pendulum.parse(d.attrib["time"], strict=False).to_date_string()
        db.hmset(f"{time}-rates", {c.attrib["currency"]: c.attrib["rate"] for c in list(d)})

        # If first loop set as latest date
        if i == 0:
            db.set("latest-rates", f"{time}")


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
    def symbol_validation(cls, b):
        # TODO: implement Regex validators
        return b


@app.route("/")
async def vat_validation(request):
    try:
        VATValidationModel(**request.query_params)
        client = zeep.Client(wsdl=VIES_URL)
        response = zeep.helpers.serialize_object(client.service.checkVat(countryCode="BE", vatNumber="0878065378"))
        return UJSONResponse({k: response[k] for k in ("name", "address", "valid")})
    except ValidationError as e:
        return UJSONResponse(e.errors())


@app.route("/api/rates")
async def rates(request):
    db = redis.Redis(host="localhost", port=6379, db=0, charset="utf-8", decode_responses=True)

    try:
        query = RatesQueryValidationModel(**request.query_params)

        # Find the date
        date = query.date
        if not date:
            date = db.get("latest-rates")

        # Get the rates data
        rates = db.hgetall(f"{date}-rates")

        # Base re-calculation
        if query.base and query.base != "EUR":
            base_rate = Decimal(rates[query.base])
            rates = {currency: Decimal(rate) / base_rate for currency, rate in rates.items()}
            rates.update({"EUR": Decimal(1) / base_rate})

        return UJSONResponse({"date": date, "rates": rates})
    except ValidationError as e:
        return UJSONResponse(e.errors())
