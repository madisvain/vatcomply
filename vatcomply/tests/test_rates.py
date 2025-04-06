from django.test import TestCase
from django.core.management import call_command


class RatesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_rates")

    def test_latest_api(self):
        response = self.client.get("/rates")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("date", response.json())
        self.assertIn("base", response.json())
        self.assertEqual(response.json()["base"], "EUR")
        self.assertIn("rates", response.json())
        self.assertEqual(len(response.json()["rates"]), 31)

    def test_date_api(self):
        response = self.client.get("/rates?date=2018-10-12")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("date", response.json())
        self.assertEqual(response.json()["date"], "2018-10-12")
        self.assertIn("base", response.json())
        self.assertEqual(response.json()["base"], "EUR")
        self.assertIn("rates", response.json())
        self.assertEqual(len(response.json()["rates"]), 33)

    def test_invalid_date_api(self):
        response = self.client.get("/rates?date=abc")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())
        self.assertIn("date", response.json()["query"])

    def test_date_weekend_api(self):
        response = self.client.get("/rates?date=2018-10-13")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("date", response.json())
        self.assertEqual(response.json()["date"], "2018-10-12")
        self.assertIn("base", response.json())
        self.assertEqual(response.json()["base"], "EUR")
        self.assertIn("rates", response.json())
        self.assertEqual(len(response.json()["rates"]), 33)

    def test_base_api(self):
        response = self.client.get("/rates?base=USD")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("date", response.json())
        self.assertIn("base", response.json())
        self.assertEqual(response.json()["base"], "USD")
        self.assertIn("rates", response.json())
        self.assertEqual(len(response.json()["rates"]), 31)
        self.assertEqual(response.json()["rates"]["USD"], 1)

    def test_symbols_api(self):
        response = self.client.get("/rates?symbols=USD,JPY,GBP")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("date", response.json())
        self.assertIn("base", response.json())
        self.assertEqual(response.json()["base"], "EUR")
        self.assertIn("rates", response.json())
        self.assertEqual(len(response.json()["rates"]), 3)

    def test_invalid_symbols_api(self):
        response = self.client.get("/rates?symbols=12345")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())
        self.assertIn("symbols", response.json()["query"])
        self.assertIsInstance(response.json()["query"]["symbols"], list)
