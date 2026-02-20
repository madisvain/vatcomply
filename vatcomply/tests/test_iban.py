from django.test import TestCase

from django_bolt.testing import TestClient

from vatcomply.api import api

# Known-good IBAN for deterministic tests
TEST_IBAN = "DE89370400440532013000"


class IBANTest(TestCase):
    def test_iban_api(self):
        with TestClient(api) as client:
            response = client.get(f"/iban?iban={TEST_IBAN}")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertTrue(data["valid"])
            self.assertEqual(data["country_code"], "DE")
            self.assertIn("bban", data)
            self.assertIn("bank_code", data)

    def test_iban_blank_api(self):
        with TestClient(api) as client:
            response = client.get("/iban?iban=")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

    def test_iban_invalid_format_api(self):
        with TestClient(api) as client:
            response = client.get("/iban?iban=123")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

    def test_iban_invalid_checksum(self):
        with TestClient(api) as client:
            response = client.get("/iban?iban=DE89370400440532013")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

    def test_non_field_validation_error(self):
        with TestClient(api) as client:
            response = client.get("/iban")  # Missing required field
            self.assertEqual(response.status_code, 422)
            self.assertIsInstance(response.json(), dict)
