from django.test import TestCase

from django_bolt.testing import TestClient

from vatcomply.api import api
from vatcomply.constants import CurrencySymbol


class CurrenciesTest(TestCase):
    def test_currencies_api(self):
        with TestClient(api) as client:
            response = client.get("/currencies")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertEqual(len(data), len(CurrencySymbol.choices))

    def test_currencies_have_name_and_symbol(self):
        with TestClient(api) as client:
            response = client.get("/currencies")
            data = response.json()
            for symbol, info in data.items():
                self.assertIn("name", info)
                self.assertIn("symbol", info)
                self.assertEqual(info["symbol"], symbol)

    def test_search_by_currency_code(self):
        with TestClient(api) as client:
            response = client.get("/currencies?search=USD")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("USD", data)
            for code in data:
                self.assertIn("USD", code.upper())

    def test_search_by_currency_name(self):
        with TestClient(api) as client:
            response = client.get("/currencies?search=dollar")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("USD", data)
            for info in data.values():
                self.assertIn("dollar", info["name"].lower())

    def test_search_case_insensitive(self):
        with TestClient(api) as client:
            response_lower = client.get("/currencies?search=usd")
            response_upper = client.get("/currencies?search=USD")
            self.assertEqual(response_lower.json(), response_upper.json())

    def test_search_no_results(self):
        with TestClient(api) as client:
            response = client.get("/currencies?search=zzzzzzz")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data, {})

    def test_metadata_fields_present(self):
        with TestClient(api) as client:
            response = client.get("/currencies?search=USD")
            data = response.json()
            usd = data["USD"]
            expected_fields = [
                "name", "symbol", "numeric_code", "currency_symbol",
                "currency_symbol_narrow", "decimal_places", "rounding",
                "countries", "official_countries", "historical",
            ]
            for field in expected_fields:
                self.assertIn(field, usd, f"Missing field: {field}")

    def test_decimal_places_usd(self):
        with TestClient(api) as client:
            response = client.get("/currencies?search=USD")
            usd = response.json()["USD"]
            self.assertEqual(usd["decimal_places"], 2)

    def test_decimal_places_jpy(self):
        with TestClient(api) as client:
            response = client.get("/currencies?search=JPY")
            jpy = response.json()["JPY"]
            self.assertEqual(jpy["decimal_places"], 0)

    def test_countries_non_empty_for_major_currencies(self):
        with TestClient(api) as client:
            response = client.get("/currencies")
            data = response.json()
            self.assertGreater(len(data["USD"]["countries"]), 0)
            self.assertGreater(len(data["EUR"]["countries"]), 0)

    def test_historical_hrk(self):
        with TestClient(api) as client:
            response = client.get("/currencies?search=HRK")
            hrk = response.json()["HRK"]
            self.assertTrue(hrk["historical"])

    def test_non_historical_usd(self):
        with TestClient(api) as client:
            response = client.get("/currencies?search=USD")
            usd = response.json()["USD"]
            self.assertFalse(usd["historical"])

    def test_currency_symbol_values(self):
        with TestClient(api) as client:
            response = client.get("/currencies")
            data = response.json()
            self.assertEqual(data["USD"]["currency_symbol"], "$")
            self.assertEqual(data["EUR"]["currency_symbol"], "\u20ac")

    def test_numeric_code(self):
        with TestClient(api) as client:
            response = client.get("/currencies?search=USD")
            usd = response.json()["USD"]
            self.assertEqual(usd["numeric_code"], "840")
