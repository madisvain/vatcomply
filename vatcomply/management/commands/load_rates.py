import httpx
import pendulum

from django.conf import settings
from django.core.management.base import BaseCommand
from xml.etree import ElementTree

from vatcomply.models import Rate

BATCH_SIZE = 500
REQUEST_TIMEOUT = 60


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

        last_90_days = bool(options["last_90_days"])
        url = settings.RATES_LAST_90_DAYS_URL if last_90_days else settings.RATES_URL

        try:
            r = httpx.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
        except httpx.HTTPError as e:
            self.stderr.write(f"Failed to fetch rates data: {e}")
            return

        envelope = ElementTree.fromstring(r.content)

        namespaces = {
            "gesmes": "http://www.gesmes.org/xml/2002-08-01",
            "eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
        }
        data = envelope.findall("./eurofxref:Cube/eurofxref:Cube[@time]", namespaces)

        batch = []
        for d in data:
            time = pendulum.parse(d.attrib["time"], strict=True)
            batch.append(
                Rate(
                    date=time,
                    rates={
                        str(c.attrib["currency"]): float(c.attrib["rate"])
                        for c in list(d)
                    },
                )
            )

        created = Rate.objects.bulk_create(
            batch,
            batch_size=BATCH_SIZE,
            ignore_conflicts=True,
        )

        self.stdout.write(
            f"Loading rates finished! Processed {len(batch)} dates "
            f"({len(created)} new, {len(batch) - len(created)} already existed)."
        )
