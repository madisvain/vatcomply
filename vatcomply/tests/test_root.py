from django.test import TestCase
from django.conf import settings
from urllib.parse import urljoin


class RootTest(TestCase):
    def test_root_endpoint(self):
        """Test the root endpoint returns correct API information"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Check all required fields are present
        self.assertIsInstance(data, dict)
        self.assertIn("name", data)
        self.assertIn("version", data)
        self.assertIn("status", data)
        self.assertIn("description", data)
        self.assertIn("documentation", data)
        self.assertIn("endpoints", data)
        self.assertIn("contact", data)

        # Check specific values
        self.assertEqual(data["name"], "VATComply API")
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["status"], "operational")
        self.assertEqual(data["description"], "VAT validation API, geolocation tools, and ECB exchange rates")
        self.assertEqual(data["documentation"], urljoin(settings.BASE_URL, "docs"))
        self.assertEqual(data["contact"], "support@vatcomply.com")

        # Check endpoints
        self.assertIsInstance(data["endpoints"], dict)
        self.assertGreater(len(data["endpoints"]), 0)

        # Check some known endpoints are present and properly formatted
        expected_endpoints = ["countries", "currencies", "geolocate", "vat", "rates"]
        for endpoint in expected_endpoints:
            self.assertIn(endpoint, data["endpoints"])
            self.assertEqual(data["endpoints"][endpoint], urljoin(settings.BASE_URL, endpoint))
