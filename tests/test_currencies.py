from starlette.testclient import TestClient

from app import app


class TestCurrenciesAPI(object):
    def test_currencies_api(self):
        with TestClient(app) as client:
            response = client.get("/api/currencies")
            assert response.status_code == 200
            assert isinstance(response.json(), dict)
            assert "EUR" in response.json()
            assert "USD" in response.json()
            assert response.json()["EUR"]["name"] == "Euro"
            assert response.json()["EUR"]["symbol"] == "€"
            assert len(response.json()) == 33
