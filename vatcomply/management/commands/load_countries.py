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
            Country.objects.update_or_create(
                iso2=country["iso2"],
                defaults={
                    "name": country["name"],
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

        self.stdout.write("Loading countries dataset finished!")
