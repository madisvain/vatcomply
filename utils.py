import json
import pendulum
import requests
import ujson

from starlette.responses import JSONResponse
from typing import Any
from xml.etree import ElementTree

from db import database, Countries, Rates
from settings import COUNTRIES_URL, RATES_URL, RATES_LAST_90_DAYS_URL


class UJSONResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        assert ujson is not None, "ujson must be installed to use UJSONResponse"
        return ujson.dumps(content, ensure_ascii=False).encode("utf-8")


async def load_rates(last_90_days=True):
    print("Loading rates ...")
    r = requests.get(RATES_LAST_90_DAYS_URL if last_90_days else RATES_URL)
    envelope = ElementTree.fromstring(r.content)

    namespaces = {
        "gesmes": "http://www.gesmes.org/xml/2002-08-01",
        "eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
    }
    data = envelope.findall("./eurofxref:Cube/eurofxref:Cube[@time]", namespaces)
    for i, d in enumerate(data):
        time = pendulum.parse(d.attrib["time"], strict=False)
        if not await database.fetch_one(
            query=Rates.select().where(Rates.c.date == time)
        ):
            await database.execute(
                query=Rates.insert(),
                values={
                    "date": time,
                    "rates": {
                        str(c.attrib["currency"]): float(c.attrib["rate"])
                        for c in list(d)
                    },
                },
            )
    print("Loading rates finised!")


async def load_countries():
    print("Loading countries ...")
    r = requests.get(COUNTRIES_URL)
    for country in r.json():
        if not await database.fetch_one(
            query=Countries.select().where(Countries.c.iso2 == country["iso2"])
        ):
            await database.execute(
                query=Countries.insert(),
                values={
                    "name": country["name"],
                    "iso2": country["iso2"],
                    "iso3": country["iso3"],
                    "numeric_code": country["numeric_code"],
                    "phone_code": country["phone_code"],
                    "capital": country["capital"],
                    "currency": country["currency"],
                    "tld": country["tld"],
                    "region": country["region"],
                    "subregion": country["subregion"],
                    "latitude": country["latitude"],
                    "longitude": country["longitude"],
                    "emoji": country["emoji"],
                },
            )
    print("Loading countries finised!")
