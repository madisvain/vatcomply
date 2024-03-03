from django.conf import settings
from django.test import TestCase


class CurrenciesTest(TestCase):
    def test_currencies_api(self):
        response = self.client.get("/currencies")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertEqual(len(response.json()), len(settings.CURRENCY_SYMBOLS))
