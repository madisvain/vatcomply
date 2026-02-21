import logging

import httpx

from django.conf import settings
from django.core.management.base import BaseCommand

from vatcomply.models import Country

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
REQUEST_TIMEOUT = 30


class Command(BaseCommand):
    help = "Load countries dataset"

    def handle(self, *args, **kwargs):
        self.stdout.write("Loading countries...")

        try:
            r = httpx.get(settings.COUNTRIES_URL, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Failed to fetch countries data: %s", e)
            self.stderr.write(f"Failed to fetch countries data: {e}")
            return

        batch = []
        for country in r.json():
            batch.append(
                Country(
                    iso2=country["iso2"],
                    name=country["name"],
                    iso3=country["iso3"],
                    numeric_code=country["numeric_code"],
                    phone_code=country["phonecode"],
                    capital=country["capital"],
                    currency=country["currency"],
                    tld=country["tld"],
                    region=country["region"],
                    subregion=country["subregion"],
                    latitude=country["latitude"],
                    longitude=country["longitude"],
                    emoji=country["emoji"],
                )
            )

        Country.objects.bulk_create(
            batch,
            batch_size=BATCH_SIZE,
            update_conflicts=True,
            unique_fields=["iso2"],
            update_fields=[
                "name",
                "iso3",
                "numeric_code",
                "phone_code",
                "capital",
                "currency",
                "tld",
                "region",
                "subregion",
                "latitude",
                "longitude",
                "emoji",
            ],
        )

        self.stdout.write(f"Loading countries dataset finished! Loaded {len(batch)} countries.")
