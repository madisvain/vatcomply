from django.test import TransactionTestCase
from django.core.management import call_command

from django_bolt.testing import TestClient

from vatcomply.api import api
from vatcomply.models import Country


class GeolocateTest(TransactionTestCase):
    def setUp(self):
        # Load countries data since geolocate endpoint depends on it
        call_command("load_countries")

    def test_geolocate_without_headers(self):
        """Test geolocate endpoint without required CDN headers"""
        with TestClient(api) as client:
            response = client.get("/geolocate")
            self.assertEqual(response.status_code, 404)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)
            self.assertEqual(
                data["detail"],
                "Country code not received from CDN headers (CF-IPCountry or Cdn-RequestCountryCode).",
            )

    def test_geolocate_with_invalid_country(self):
        """Test geolocate endpoint with invalid country code"""
        with TestClient(api) as client:
            response = client.get(
                "/geolocate",
                headers={
                    "cf-ipcountry": "XX",  # Invalid country code
                    "cf-connecting-ip": "1.2.3.4",
                },
            )
            self.assertEqual(response.status_code, 404)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)
            self.assertEqual(
                data["detail"], "Data for country code `XX` not found."
            )

    def test_geolocate_success(self):
        """Test successful geolocate endpoint call"""
        with TestClient(api) as client:
            response = client.get(
                "/geolocate",
                headers={
                    "cf-ipcountry": "DE",
                    "cf-connecting-ip": "85.214.132.117",
                },
            )

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, dict)

            country = Country.objects.get(iso2="DE")

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

    def test_geolocate_with_bunny_header(self):
        """Test geolocate endpoint with Bunny.net CDN header"""
        with TestClient(api) as client:
            response = client.get(
                "/geolocate",
                headers={
                    "cdn-requestcountrycode": "FR",
                },
            )

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, dict)

            country = Country.objects.get(iso2="FR")

            self.assertEqual(data["country_code"], "FR")
            self.assertEqual(data["iso2"], country.iso2)
            self.assertEqual(data["name"], country.name)
