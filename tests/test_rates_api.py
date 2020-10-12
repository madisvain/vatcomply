from starlette.testclient import TestClient

from app import app


class TestRatesAPI(object):
    def test_latest_api(self):
        with TestClient(app) as client:
            response = client.get("/rates", headers={"Authorization": "Token test-token"})
            assert response.status_code == 200
            assert isinstance(response.json(), dict)
            assert "date" in response.json()
            assert "base" in response.json()
            assert response.json()["base"] == "EUR"
            assert "rates" in response.json()
            assert len(response.json()["rates"]) == 33

    def test_date_api(self):
        with TestClient(app) as client:
            response = client.get("/rates?date=2018-10-12", headers={"Authorization": "Token test-token"})
            assert response.status_code == 200
            assert isinstance(response.json(), dict)
            assert "date" in response.json()
            assert response.json()["date"] == "2018-10-12"
            assert "base" in response.json()
            assert response.json()["base"] == "EUR"
            assert "rates" in response.json()
            assert len(response.json()["rates"]) == 33

    def test_invalid_date_api(self):
        with TestClient(app) as client:
            response = client.get("/rates?date=abc", headers={"Authorization": "Token test-token"})
            assert response.status_code == 400
            assert isinstance(response.json(), list)

    def test_date_weekend_api(self):
        with TestClient(app) as client:
            response = client.get("/rates?date=2018-10-13", headers={"Authorization": "Token test-token"})
            assert response.status_code == 200
            assert isinstance(response.json(), dict)
            assert "date" in response.json()
            assert response.json()["date"] == "2018-10-12"
            assert "base" in response.json()
            assert response.json()["base"] == "EUR"
            assert "rates" in response.json()
            assert len(response.json()["rates"]) == 33

    def test_base_api(self):
        with TestClient(app) as client:
            response = client.get("/rates?base=USD", headers={"Authorization": "Token test-token"})
            assert response.status_code == 200
            assert isinstance(response.json(), dict)
            assert "date" in response.json()
            assert "base" in response.json()
            assert response.json()["base"] == "USD"
            assert "rates" in response.json()
            assert len(response.json()["rates"]) == 33
            assert response.json()["rates"]["USD"] == 1

    def test_symbols_api(self):
        with TestClient(app) as client:
            response = client.get("/rates?symbols=USD,JPY,GBP", headers={"Authorization": "Token test-token"})
            assert response.status_code == 200
            assert isinstance(response.json(), dict)
            assert "date" in response.json()
            assert "base" in response.json()
            assert response.json()["base"] == "EUR"
            assert "rates" in response.json()
            assert len(response.json()["rates"]) == 3

    def test_invalid_symbols_api(self):
        with TestClient(app) as client:
            response = client.get("/rates?symbols=12345", headers={"Authorization": "Token test-token"})
            assert response.status_code == 400
            assert isinstance(response.json(), list)
