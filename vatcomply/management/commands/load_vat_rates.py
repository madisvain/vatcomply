import logging
import os
from collections import defaultdict
from datetime import date

import zeep
import zeep.helpers

from django.core.management.base import BaseCommand

from vatcomply.models import Country, VATRate

logger = logging.getLogger(__name__)

WSDL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "wsdl", "VatRetrievalService.wsdl"
)

EU_MEMBER_STATES = [
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES",
    "FI", "FR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PL", "PT", "RO", "SE", "SI", "SK",
]

# TEDB uses EL for Greece; map to ISO 3166 for Country model lookups
TEDB_TO_ISO = {"EL": "GR"}


class Command(BaseCommand):
    help = "Load EU VAT rates from the TEDB SOAP service"

    def handle(self, *args, **options):
        self.stdout.write("Loading VAT rates from TEDB...")

        try:
            client = zeep.Client(wsdl=WSDL_PATH)
        except Exception as e:
            logger.error("Failed to load TEDB WSDL: %s", e)
            self.stderr.write(f"Failed to load WSDL: {e}")
            return

        today = date.today().isoformat()

        try:
            response = client.service.retrieveVatRates(
                memberStates={"isoCode": EU_MEMBER_STATES},
                situationOn=today,
            )
        except Exception as e:
            logger.error("TEDB SOAP call failed: %s", e)
            self.stderr.write(f"TEDB SOAP call failed: {e}")
            return

        data = zeep.helpers.serialize_object(response)
        vat_results = data.get("vatRateResults", [])

        if not vat_results:
            self.stderr.write("No VAT rate results returned from TEDB.")
            return

        # Group results by member state
        by_country = defaultdict(lambda: {
            "standard_rate": 0.0,
            "reduced_rates": [],
            "super_reduced_rate": None,
            "parking_rate": None,
            "rate_comments": {},
            "rate_categories": {},
        })

        for result in vat_results:
            ms = result["memberState"]
            rate_type = result["type"]  # STANDARD or REDUCED
            rate_value_type = result["rate"]["type"]  # DEFAULT, REDUCED_RATE, etc.
            value = result["rate"].get("value")

            if value is None:
                continue

            info = by_country[ms]

            if rate_type == "STANDARD" and rate_value_type == "DEFAULT":
                info["standard_rate"] = float(value)
            elif rate_value_type == "REDUCED_RATE":
                if float(value) not in info["reduced_rates"]:
                    info["reduced_rates"].append(float(value))
            elif rate_value_type == "SUPER_REDUCED_RATE":
                info["super_reduced_rate"] = float(value)
            elif rate_value_type == "PARKING_RATE":
                info["parking_rate"] = float(value)

            # Extract TEDB comment/category annotation for this rate
            comment = result.get("comment", "")
            category = result.get("category")
            annotation = comment or (category.get("description", "") if category else "")
            if annotation:
                key = str(float(value))
                if key not in info["rate_comments"]:
                    info["rate_comments"][key] = []
                if annotation not in info["rate_comments"][key]:
                    info["rate_comments"][key].append(annotation)

            # Extract structured category-to-rate mapping
            if category:
                identifier = category.get("identifier", "")
                if identifier:
                    key = identifier.lower()
                    if key not in info["rate_categories"]:
                        info["rate_categories"][key] = []
                    if float(value) not in info["rate_categories"][key]:
                        info["rate_categories"][key].append(float(value))

        # Build country name + currency lookup
        country_lookup = {}
        for country in Country.objects.all():
            country_lookup[country.iso2] = country

        batch = []
        for ms in EU_MEMBER_STATES:
            info = by_country.get(ms)
            if not info:
                continue

            iso_code = TEDB_TO_ISO.get(ms, ms)
            country = country_lookup.get(iso_code)
            country_name = country.name if country else ms
            currency = country.currency if country else ""

            # Sort reduced rates for consistent output
            info["reduced_rates"].sort()
            for cat_rates in info["rate_categories"].values():
                cat_rates.sort()

            batch.append(
                VATRate(
                    country_code=ms,
                    country_name=country_name,
                    standard_rate=info["standard_rate"],
                    reduced_rates=info["reduced_rates"],
                    super_reduced_rate=info["super_reduced_rate"],
                    parking_rate=info["parking_rate"],
                    currency=currency,
                    member_state=True,
                    rate_comments=info["rate_comments"],
                    rate_categories=info["rate_categories"],
                )
            )

        VATRate.objects.bulk_create(
            batch,
            update_conflicts=True,
            unique_fields=["country_code"],
            update_fields=[
                "country_name", "standard_rate", "reduced_rates",
                "super_reduced_rate", "parking_rate", "currency", "member_state",
                "rate_comments",
                "rate_categories",
            ],
        )

        self.stdout.write(f"Loaded VAT rates for {len(batch)} EU member states.")
