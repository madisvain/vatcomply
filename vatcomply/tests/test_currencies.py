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
