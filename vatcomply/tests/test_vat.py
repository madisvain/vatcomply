from django.test import TestCase
from unittest.mock import patch, AsyncMock, MagicMock

from django_bolt.testing import TestClient

from vatcomply.api import api


class VATTest(TestCase):
    def test_vat_blank_api(self):
        with TestClient(api) as client:
            response = client.get("/vat?vat_number=")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

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
            self.assertIn("GB", data["detail"])

    @patch("vatcomply.api._vat_client")
    def test_vat_valid_number(self, mock_client):
        mock_service = MagicMock()
        mock_service.checkVat = AsyncMock(return_value={
            "valid": True,
            "vatNumber": "101600930",
            "countryCode": "EE",
            "name": "Test Company",
            "address": "Test Address",
        })
        mock_client.service = mock_service

        with TestClient(api) as client:
            response = client.get("/vat?vat_number=EE101600930")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["valid"])
            self.assertEqual(data["country_code"], "EE")
            self.assertEqual(data["name"], "Test Company")

    @patch("vatcomply.api._vat_client")
    def test_vat_service_fault(self, mock_client):
        from zeep.exceptions import Fault
        mock_service = MagicMock()
        mock_service.checkVat = AsyncMock(side_effect=Fault("INVALID_INPUT"))
        mock_client.service = mock_service

        with TestClient(api) as client:
            response = client.get("/vat?vat_number=DE123456789")
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIsInstance(data, dict)
            self.assertIn("detail", data)

    def test_non_field_validation_error(self):
        with TestClient(api) as client:
            response = client.get("/vat")  # Missing required field
            self.assertEqual(response.status_code, 422)
            self.assertIsInstance(response.json(), dict)
