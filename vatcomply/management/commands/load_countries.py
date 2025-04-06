import httpx

from django.conf import settings
from django.core.management.base import BaseCommand

from vatcomply.models import Country


class Command(BaseCommand):
    help = "Load countries dataset"

    def handle(self, *args, **kwargs):
        self.stdout.write("Loading countries...")

        r = httpx.get(settings.COUNTRIES_URL)
        for country in r.json():
            Country.objects.bulk_create(
                [
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
                ],
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

        self.stdout.write("Loading countries dataset finished!")
