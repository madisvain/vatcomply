from django.test import TestCase


class VATTest(TestCase):
    def test_vat_api(self):
        response = self.client.get("/vat?vat_number=EE101600930")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)

    def test_vat_blank_api(self):
        response = self.client.get("/vat?vat_number=")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)

    def test_vat_invalid_format_api(self):
        response = self.client.get("/vat?vat_number=123")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())
        self.assertIn("vat_number", response.json()["query"])
        self.assertEqual(
            response.json()["query"]["vat_number"][0],
            "Value error, Invalid VAT number format. Expected format: Two-letter country code followed by 8-12 digits or letters.",
        )

    def test_vat_brexit_api(self):
        response = self.client.get("/vat?vat_number=GB123456789")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())
        self.assertIn("vat_number", response.json()["query"])
        self.assertEqual(
            response.json()["query"]["vat_number"][0],
            "Value error, As of 01/01/2021, the VoW service to validate UK (GB) VAT numbers ceased to exist while a new service to validate VAT numbers of businesses operating under the Protocol on Ireland and Northern Ireland appeared. These VAT numbers are starting with the “XI” prefix.",
        )
