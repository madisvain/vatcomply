from django.test import TransactionTestCase
from unittest.mock import patch
from zeep.exceptions import Fault

from django_bolt.testing import TestClient

from vatcomply.api import api


class VATTest(TransactionTestCase):
    def test_vat_api(self):
        with TestClient(api) as client:
            response = client.get("/vat?vat_number=EE101600930")
            self.assertEqual(response.status_code, 200)
            self.assertIsInstance(response.json(), dict)

    def test_vat_blank_api(self):
        with TestClient(api) as client:
            response = client.get("/vat?vat_number=")
            self.assertEqual(response.status_code, 400)
            self.assertIsInstance(response.json(), dict)

    def test_vat_invalid_format_api(self):
        with TestClient(api) as client:
            response = client.get("/vat?vat_number=123")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

    def test_vat_brexit_api(self):
        with TestClient(api) as client:
            response = client.get("/vat?vat_number=GB123456789")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

    @patch("zeep.AsyncClient")
    def test_vat_service_fault(self, mock_client):
        # Mock SOAP fault
        mock_client.return_value.service.checkVat.side_effect = Fault("SOAP fault")

        with TestClient(api) as client:
            response = client.get("/vat?vat_number=DE123456789")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

    def test_validation_error_handling(self):
        with TestClient(api) as client:
            # Use real endpoint to test validation handling
            response = client.get("/vat?vat_number=123")  # Invalid format
            self.assertEqual(response.status_code, 400)
            self.assertIsInstance(response.json(), dict)

    def test_non_field_validation_error(self):
        with TestClient(api) as client:
            # Use real endpoint with non-field error
            response = client.get("/vat")  # Missing required field
            self.assertEqual(response.status_code, 422)
            self.assertIsInstance(response.json(), dict)
