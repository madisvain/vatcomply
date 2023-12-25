import httpx
import pendulum

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from xml.etree import ElementTree

from vatcomply.models import Rate


class Command(BaseCommand):
    help = "Load ECB rates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--last-90-days",
            action="store_true",
            help="Load rates for last 90 days",
        )

    def handle(self, *args, **options):
        self.stdout.write("Loading rates...")

        last_90_days = True if options["last_90_days"] else False
        r = httpx.get(
            settings.RATES_LAST_90_DAYS_URL if last_90_days else settings.RATES_URL
        )
        envelope = ElementTree.fromstring(r.content)

        namespaces = {
            "gesmes": "http://www.gesmes.org/xml/2002-08-01",
            "eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
        }
        data = envelope.findall("./eurofxref:Cube/eurofxref:Cube[@time]", namespaces)
        skipped = 0
        for i, d in enumerate(data):
            time = pendulum.parse(d.attrib["time"], strict=False)
            try:
                Rate.objects.create(
                    date=time,
                    rates={
                        str(c.attrib["currency"]): float(c.attrib["rate"])
                        for c in list(d)
                    },
                )
            except IntegrityError:
                skipped += 1

        self.stdout.write(
            "Loading rates finished! Skipped {} existing rates.".format(skipped)
        )
