from django.test import TransactionTestCase
from django.core.management import call_command

from django_bolt.testing import TestClient

from vatcomply.api import api
from vatcomply.models import Country


class CountriesTest(TransactionTestCase):
    def setUp(self):
        call_command("load_countries")

    def test_countries_api(self):
        with TestClient(api) as client:
            response = client.get("/countries")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), Country.objects.count())
