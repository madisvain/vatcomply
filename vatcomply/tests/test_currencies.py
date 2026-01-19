from django.conf import settings
from django.test import TransactionTestCase

from django_bolt.testing import TestClient

from vatcomply.api import api


class CurrenciesTest(TransactionTestCase):
    def test_currencies_api(self):
        with TestClient(api) as client:
            response = client.get("/currencies")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertEqual(len(data), len(settings.CURRENCY_SYMBOLS))
