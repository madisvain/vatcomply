import logging

import httpx
import pendulum
import sentry_sdk
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from xml.etree import ElementTree

from vatcomply.models import Rate

logger = logging.getLogger(__name__)

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

        previous_latest = Rate.objects.order_by("-date").values_list("date", flat=True).first()
        logger.info(
            "load_rates starting (previous latest date: %s)",
            previous_latest.isoformat() if previous_latest else "none",
        )

        last_90_days = bool(options["last_90_days"])
        url = settings.RATES_LAST_90_DAYS_URL if last_90_days else settings.RATES_URL

        try:
            r = httpx.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
        except httpx.HTTPError as e:
            logger.exception("Failed to fetch rates data from ECB")
            sentry_sdk.capture_exception(e)
            raise CommandError(f"Failed to fetch rates data from ECB: {e}") from e

        try:
            envelope = ElementTree.fromstring(r.content)
        except ElementTree.ParseError as e:
            logger.exception("Failed to parse ECB rates XML")
            sentry_sdk.capture_exception(e)
            raise CommandError(f"Failed to parse ECB rates XML: {e}") from e

        namespaces = {
            "gesmes": "http://www.gesmes.org/xml/2002-08-01",
            "eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
        }
        data = envelope.findall("./eurofxref:Cube/eurofxref:Cube[@time]", namespaces)

        if not data:
            message = "ECB rates XML contained no rate cubes"
            logger.error(message)
            sentry_sdk.capture_message(message, level="error")
            raise CommandError(message)

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

        new_latest = Rate.objects.order_by("-date").values_list("date", flat=True).first()
        created_count = len(created)
        existing_count = len(batch) - created_count

        summary = (
            f"Loading rates finished! Processed {len(batch)} dates "
            f"({created_count} new, {existing_count} already existed). "
            f"Latest date: {new_latest.isoformat() if new_latest else 'none'}."
        )
        self.stdout.write(summary)
        logger.info(summary)
