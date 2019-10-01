import asyncio
import pendulum
import requests

from xml.etree import ElementTree

from db import database, Rates
from settings import RATES_URL


async def load_rates():
    await database.connect()

    r = requests.get(RATES_URL)
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

    await database.disconnect()


loop = asyncio.get_event_loop()
task = loop.create_task(load_rates())

try:
    loop.run_until_complete(task)
except asyncio.CancelledError:
    pass
