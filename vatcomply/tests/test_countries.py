from django.test import TestCase
from django.core.management import call_command

from vatcomply.models import Country


class CountriesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_countries")

    def test_countries_api(self):
        response = self.client.get("/countries")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertEqual(len(response.json()), Country.objects.count())
