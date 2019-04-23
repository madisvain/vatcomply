import pendulum
import uvicorn
import redis
import requests
import zeep

from datetime import datetime
from decimal import Decimal
from xml.etree import ElementTree

from pydantic import BaseModel, ValidationError, validator
from pydantic.dataclasses import dataclass
from starlette.applications import Starlette
from starlette.responses import UJSONResponse

HISTORIC_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
VIES_URL = "http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl"

app = Starlette(debug=True)


@app.on_event('startup')
def load_rates():
    db = redis.Redis(host='localhost', port=6379, db=0)

    r = requests.get(HISTORIC_RATES_URL)
    envelope = ElementTree.fromstring(r.content)

    namespaces = {
        "gesmes": "http://www.gesmes.org/xml/2002-08-01",
        "eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
    }
    data = envelope.findall("./eurofxref:Cube/eurofxref:Cube[@time]", namespaces)
    for d in data:
        time = datetime.strptime(d.attrib["time"], "%Y-%m-%d").date()
        rates = db.hgetall(f'{time}-rates')
        if not rates:
            db.hmset(f'{time}-rates', {c.attrib["currency"]: c.attrib["rate"] for c in list(d)})


class VATValidationModel(BaseModel):
    vat_number: str

    @validator("vat_number")
    def format_validation(cls, v):
        # TODO: implement Regex validators
        return v


@app.route("/")
async def vat_validation(request):
    try:
        VATValidationModel(**request.query_params)
        client = zeep.Client(wsdl=VIES_URL)
        response = zeep.helpers.serialize_object(client.service.checkVat(countryCode="BE", vatNumber="0878065378"))
        return UJSONResponse({k: response[k] for k in ("name", "address", "valid")})
    except ValidationError as e:
        return UJSONResponse(e.errors())


@app.route("/rates")
async def rates(request):
    db = redis.Redis(host='localhost', port=6379, db=0)

    try:
        time = pendulum.now().subtract(days=4)
        rates = db.hgetall(f'{time.to_date_string()}-rates')
        return UJSONResponse(rates)
    except ValidationError as e:
        return UJSONResponse(e.errors())
