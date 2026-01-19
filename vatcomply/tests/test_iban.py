from django.test import TransactionTestCase
from schwifty import IBAN as SchwiftyIBAN

from django_bolt.testing import TestClient

from vatcomply.api import api


class IBANTest(TransactionTestCase):
    def test_iban_api(self):
        with TestClient(api) as client:
            response = client.get(f"/iban?iban={SchwiftyIBAN.random()}")
            self.assertEqual(response.status_code, 200)
            self.assertIsInstance(response.json(), dict)

    def test_iban_blank_api(self):
        with TestClient(api) as client:
            response = client.get("/iban?iban=")
            self.assertEqual(response.status_code, 400)
            self.assertIsInstance(response.json(), dict)

    def test_iban_invalid_format_api(self):
        with TestClient(api) as client:
            response = client.get("/iban?iban=123")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

    def test_iban_service_fault(self):
        with TestClient(api) as client:
            response = client.get("/iban?iban=DE89370400440532013")
            self.assertEqual(response.status_code, 400)
            self.assertIsInstance(response.json(), dict)

    def test_validation_error_handling(self):
        with TestClient(api) as client:
            # Use real endpoint to test validation handling
            response = client.get("/iban?iban=123")  # Invalid format
            self.assertEqual(response.status_code, 400)
            self.assertIsInstance(response.json(), dict)

    def test_non_field_validation_error(self):
        with TestClient(api) as client:
            # Use real endpoint with non-field error
            response = client.get("/iban")  # Missing required field
            self.assertEqual(response.status_code, 422)
            self.assertIsInstance(response.json(), dict)
