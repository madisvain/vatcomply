from django.test import TestCase
from schwifty import IBAN


class IBANTest(TestCase):
    def test_iban_api(self):
        response = self.client.get(f"/iban?iban={IBAN.random()}")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)

    def test_iban_blank_api(self):
        response = self.client.get("/iban?iban=")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)

    def test_iban_invalid_format_api(self):
        response = self.client.get("/iban?iban=123")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())
        self.assertIn("iban", response.json()["query"])
        self.assertEqual(
            response.json()["query"]["iban"][0],
            "Invalid characters in IBAN 123",
        )

    def test_iban_service_fault(self):
        response = self.client.get("/iban?iban=DE89370400440532013")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())
        self.assertIn("iban", response.json()["query"])

    def test_validation_error_handling(self):
        # Use real endpoint to test validation handling
        response = self.client.get("/iban?iban=123")  # Invalid format
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())

    def test_non_field_validation_error(self):
        # Use real endpoint with non-field error
        response = self.client.get("/iban")  # Missing required field
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())
