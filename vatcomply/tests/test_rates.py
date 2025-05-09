from django.test import TestCase, override_settings
from django.core.management import call_command
from vatcomply.middleware import BackgroundTasksMiddleware


class RatesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_rates")

    def test_latest_api(self):
        response = self.client.get("/rates")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("date", response.json())
        self.assertIn("base", response.json())
        self.assertEqual(response.json()["base"], "EUR")
        self.assertIn("rates", response.json())
        self.assertEqual(len(response.json()["rates"]), 31)

    def test_date_api(self):
        response = self.client.get("/rates?date=2018-10-12")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("date", response.json())
        self.assertEqual(response.json()["date"], "2018-10-12")
        self.assertIn("base", response.json())
        self.assertEqual(response.json()["base"], "EUR")
        self.assertIn("rates", response.json())
        self.assertEqual(len(response.json()["rates"]), 33)

    def test_invalid_date_api(self):
        response = self.client.get("/rates?date=abc")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())
        self.assertIn("date", response.json()["query"])

    def test_date_weekend_api(self):
        response = self.client.get("/rates?date=2018-10-13")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("date", response.json())
        self.assertEqual(response.json()["date"], "2018-10-12")
        self.assertIn("base", response.json())
        self.assertEqual(response.json()["base"], "EUR")
        self.assertIn("rates", response.json())
        self.assertEqual(len(response.json()["rates"]), 33)

    def test_base_api(self):
        response = self.client.get("/rates?base=USD")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("date", response.json())
        self.assertIn("base", response.json())
        self.assertEqual(response.json()["base"], "USD")
        self.assertIn("rates", response.json())
        self.assertEqual(len(response.json()["rates"]), 31)
        self.assertEqual(response.json()["rates"]["USD"], 1)

    def test_invalid_base_currency(self):
        response = self.client.get("/rates?base=INVALID")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())
        self.assertIn("base", response.json()["query"])
        self.assertEqual(
            response.json()["query"]["base"][0],
            "Value error, Base currency INVALID is not supported.",
        )

    def test_symbols_api(self):
        response = self.client.get("/rates?symbols=USD,JPY,GBP")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("date", response.json())
        self.assertIn("base", response.json())
        self.assertEqual(response.json()["base"], "EUR")
        self.assertIn("rates", response.json())
        self.assertEqual(len(response.json()["rates"]), 3)

    def test_invalid_symbols_api(self):
        response = self.client.get("/rates?symbols=12345")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("query", response.json())
        self.assertIn("symbols", response.json()["query"])
        self.assertIsInstance(response.json()["query"]["symbols"], list)

    def test_non_string_symbols(self):
        from vatcomply.schemas import RatesQueryParamsSchema

        # Test with a string of comma-separated values
        schema = RatesQueryParamsSchema(base="EUR", symbols="USD,GBP")
        self.assertEqual(schema.symbols, ["USD", "GBP"])

        # Test with None value
        schema = RatesQueryParamsSchema(base="EUR", symbols=None)
        self.assertIsNone(schema.symbols)

        # Test with invalid type (should raise ValidationError)
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            RatesQueryParamsSchema(base="EUR", symbols=["USD", "GBP"])

    @override_settings(BACKGROUND_SCHEDULER=True)
    async def test_background_scheduler_middleware(self):
        # Mock app that just returns
        async def mock_app(scope, receive, send):
            return None

        # Test middleware initialization
        middleware = BackgroundTasksMiddleware(mock_app)

        # Mock the lifespan startup message
        scope = {"type": "lifespan"}

        async def receive():
            return {"type": "lifespan.startup"}

        async def send(message):
            pass

        # Should not raise any exceptions
        await middleware(scope, receive, send)
