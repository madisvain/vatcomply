from django.test import TestCase
from django.core.management import call_command

from vatcomply.models import Country


class GeolocateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Load countries data since geolocate endpoint depends on it
        call_command("load_countries")

    def test_geolocate_without_headers(self):
        """Test geolocate endpoint without required CloudFlare headers"""
        response = self.client.get("/geolocate")
        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("error", response.json())
        self.assertEqual(
            response.json()["error"],
            "Country code not received from CloudFlare headers `CF-IPCountry`.",
        )

    def test_geolocate_with_invalid_country(self):
        """Test geolocate endpoint with invalid country code"""
        response = self.client.get(
            "/geolocate",
            HTTP_CF_IPCOUNTRY="XX",  # Invalid country code
            HTTP_CF_CONNECTING_IP="1.2.3.4",
        )
        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("error", response.json())
        self.assertEqual(
            response.json()["error"], "Data for country code `XX` not found."
        )

    def test_geolocate_success(self):
        """Test successful geolocate endpoint call"""
        response = self.client.get(
            "/geolocate", HTTP_CF_IPCOUNTRY="DE", HTTP_CF_CONNECTING_IP="85.214.132.117"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)

        country = Country.objects.get(iso2="DE")

        data = response.json()
        self.assertEqual(data["country_code"], "DE")
        self.assertEqual(data["iso2"], country.iso2)
        self.assertEqual(data["iso3"], country.iso3)
        self.assertEqual(data["name"], country.name)
        self.assertEqual(data["numeric_code"], country.numeric_code)
        self.assertEqual(data["phone_code"], country.phone_code)
        self.assertEqual(data["capital"], country.capital)
        self.assertEqual(data["currency"], country.currency)
        self.assertEqual(data["tld"], country.tld)
        self.assertEqual(data["region"], country.region)
        self.assertEqual(data["subregion"], country.subregion)
        self.assertEqual(data["latitude"], country.latitude)
        self.assertEqual(data["longitude"], country.longitude)
        self.assertEqual(data["emoji"], country.emoji)
        self.assertEqual(data["ip"], "85.214.132.117")
