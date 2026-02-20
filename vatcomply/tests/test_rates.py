from django.test import TestCase
from django.core.management import call_command

from django_bolt.testing import TestClient

from vatcomply.api import api


class RatesTest(TestCase):
    def setUp(self):
        call_command("load_rates")

    def test_latest_api(self):
        with TestClient(api) as client:
            response = client.get("/rates")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("date", data)
            self.assertIn("base", data)
            self.assertEqual(data["base"], "EUR")
            self.assertIn("rates", data)
            self.assertGreater(len(data["rates"]), 0)
            # EUR should always be 1.0 when base is EUR
            self.assertEqual(data["rates"].get("EUR"), 1.0)

    def test_date_api(self):
        with TestClient(api) as client:
            response = client.get("/rates?date=2018-10-12")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("date", data)
            self.assertEqual(data["date"], "2018-10-12")
            self.assertIn("base", data)
            self.assertEqual(data["base"], "EUR")
            self.assertIn("rates", data)
            self.assertGreater(len(data["rates"]), 0)

    def test_invalid_date_api(self):
        with TestClient(api) as client:
            response = client.get("/rates?date=abc")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

    def test_date_weekend_api(self):
        with TestClient(api) as client:
            response = client.get("/rates?date=2018-10-13")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("date", data)
            # Weekend should fall back to Friday
            self.assertEqual(data["date"], "2018-10-12")
            self.assertIn("base", data)
            self.assertEqual(data["base"], "EUR")
            self.assertIn("rates", data)
            self.assertGreater(len(data["rates"]), 0)

    def test_base_api(self):
        with TestClient(api) as client:
            response = client.get("/rates?base=USD")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("date", data)
            self.assertIn("base", data)
            self.assertEqual(data["base"], "USD")
            self.assertIn("rates", data)
            self.assertGreater(len(data["rates"]), 0)
            self.assertEqual(data["rates"]["USD"], 1)

    def test_invalid_base_currency(self):
        with TestClient(api) as client:
            response = client.get("/rates?base=INVALID")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

    def test_symbols_api(self):
        with TestClient(api) as client:
            response = client.get("/rates?symbols=USD,JPY,GBP")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("date", data)
            self.assertIn("base", data)
            self.assertEqual(data["base"], "EUR")
            self.assertIn("rates", data)
            self.assertEqual(len(data["rates"]), 3)
            self.assertIn("USD", data["rates"])
            self.assertIn("JPY", data["rates"])
            self.assertIn("GBP", data["rates"])

    def test_invalid_symbols_api(self):
        with TestClient(api) as client:
            response = client.get("/rates?symbols=12345")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)
