import json
import pendulum
import requests

from xml.etree import ElementTree

from db import database, Countries, Rates
from settings import RATES_URL, RATES_LAST_90_DAYS_URL


async def load_rates(last_90_days=True):
    r = requests.get(RATES_LAST_90_DAYS_URL if last_90_days else RATES_URL)
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


async def load_countries():
    with open('countries/countries.json') as f:
        data = json.load(f)
        for country in data:
            if not await database.fetch_one(query=Countries.select().where(Countries.c.iso2 == country["iso2"])):
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
