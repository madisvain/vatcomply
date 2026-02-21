from unittest.mock import patch, MagicMock

from django.test import TransactionTestCase
from django.core.management import call_command

from django_bolt.testing import TestClient

from vatcomply.api import api
from vatcomply.models import Country
from vatcomply.tests.fixtures import MOCK_COUNTRIES_JSON


def _mock_load_countries():
    """Load countries from fixture instead of hitting the network."""
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_COUNTRIES_JSON
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=mock_response):
        call_command("load_countries")


class CountriesTest(TransactionTestCase):
    # Uses TransactionTestCase because setUp calls management commands that write to DB

    def setUp(self):
        _mock_load_countries()

    def test_countries_api(self):
        with TestClient(api) as client:
            response = client.get("/countries")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), Country.objects.count())

    # --- search ---

    def test_search_by_name(self):
        with TestClient(api) as client:
            response = client.get("/countries?search=Estonia")
            data = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertTrue(any(c["name"] == "Estonia" for c in data))

    def test_search_by_iso2(self):
        with TestClient(api) as client:
            response = client.get("/countries?search=EE")
            data = response.json()
            self.assertTrue(any(c["iso2"] == "EE" for c in data))

    def test_search_by_iso3(self):
        with TestClient(api) as client:
            response = client.get("/countries?search=EST")
            data = response.json()
            self.assertTrue(any(c["iso3"] == "EST" for c in data))

    def test_search_case_insensitive(self):
        with TestClient(api) as client:
            response = client.get("/countries?search=estonia")
            data = response.json()
            self.assertTrue(any(c["name"] == "Estonia" for c in data))

    def test_search_no_results(self):
        with TestClient(api) as client:
            response = client.get("/countries?search=ZZZZNOTACOUNTRY")
            data = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 0)

    # --- region ---

    def test_filter_by_region(self):
        with TestClient(api) as client:
            response = client.get("/countries?region=Europe")
            data = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertGreater(len(data), 0)
            self.assertTrue(all(c["region"] == "Europe" for c in data))

    def test_filter_by_region_case_insensitive(self):
        with TestClient(api) as client:
            response = client.get("/countries?region=europe")
            data = response.json()
            self.assertGreater(len(data), 0)
            self.assertTrue(all(c["region"] == "Europe" for c in data))

    def test_filter_by_region_no_results(self):
        with TestClient(api) as client:
            response = client.get("/countries?region=Atlantis")
            data = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 0)

    # --- subregion ---

    def test_filter_by_subregion(self):
        with TestClient(api) as client:
            response = client.get("/countries?subregion=Northern Europe")
            data = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertGreater(len(data), 0)
            self.assertTrue(all(c["subregion"] == "Northern Europe" for c in data))

    def test_filter_by_subregion_case_insensitive(self):
        with TestClient(api) as client:
            response = client.get("/countries?subregion=northern europe")
            data = response.json()
            self.assertGreater(len(data), 0)
            self.assertTrue(all(c["subregion"] == "Northern Europe" for c in data))

    # --- currency ---

    def test_filter_by_currency(self):
        with TestClient(api) as client:
            response = client.get("/countries?currency=EUR")
            data = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertGreater(len(data), 0)
            self.assertTrue(all(c["currency"] == "EUR" for c in data))

    def test_filter_by_currency_case_insensitive(self):
        with TestClient(api) as client:
            response = client.get("/countries?currency=eur")
            data = response.json()
            self.assertGreater(len(data), 0)
            self.assertTrue(all(c["currency"] == "EUR" for c in data))

    def test_filter_by_currency_no_results(self):
        with TestClient(api) as client:
            response = client.get("/countries?currency=ZZZCUR")
            data = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 0)

    # --- combined filters ---

    def test_combined_region_and_currency(self):
        with TestClient(api) as client:
            response = client.get("/countries?region=Europe&currency=EUR")
            data = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertGreater(len(data), 0)
            self.assertTrue(all(c["region"] == "Europe" and c["currency"] == "EUR" for c in data))

    def test_combined_search_and_region(self):
        with TestClient(api) as client:
            response = client.get("/countries?search=land&region=Europe")
            data = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertTrue(all(c["region"] == "Europe" for c in data))

    def test_combined_filters_no_results(self):
        with TestClient(api) as client:
            response = client.get("/countries?region=Europe&currency=USD")
            data = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 0)
