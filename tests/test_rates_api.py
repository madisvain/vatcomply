from starlette.testclient import TestClient

from app import app


class TestRatesAPI(object):
    def test_latest_api(self):
        client = TestClient(app)

        response = client.get("/api/rates")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
        assert "date" in response.json()
        assert "base" in response.json()
        assert response.json()["base"] == "EUR"
        assert "rates" in response.json()
        assert len(response.json()["rates"]) == 32

    def test_date_api(self):
        client = TestClient(app)

        response = client.get("/api/rates?date=2018-10-12")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
        assert "date" in response.json()
        assert response.json()["date"] == "2018-10-12"
        assert "base" in response.json()
        assert response.json()["base"] == "EUR"
        assert "rates" in response.json()
        assert len(response.json()["rates"]) == 32

    def test_invalid_date_api(self):
        client = TestClient(app)

        response = client.get("/api/rates?date=abc")
        assert response.status_code == 400
        assert isinstance(response.json(), list)

    def test_date_weekend_api(self):
        client = TestClient(app)

        response = client.get("/api/rates?date=2018-10-13")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
        assert "date" in response.json()
        assert response.json()["date"] == "2018-10-12"
        assert "base" in response.json()
        assert response.json()["base"] == "EUR"
        assert "rates" in response.json()
        assert len(response.json()["rates"]) == 32

    def test_base_api(self):
        client = TestClient(app)

        response = client.get("/api/rates?base=USD")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
        assert "date" in response.json()
        assert "base" in response.json()
        assert response.json()["base"] == "USD"
        assert "rates" in response.json()
        assert len(response.json()["rates"]) == 33
        assert response.json()["rates"]["USD"] == 1

    def test_symbols_api(self):
        client = TestClient(app)

        response = client.get("/api/rates?symbols=USD,JPY,GBP")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
        assert "date" in response.json()
        assert "base" in response.json()
        assert response.json()["base"] == "EUR"
        assert "rates" in response.json()
        assert len(response.json()["rates"]) == 3

    def test_invalid_symbols_api(self):
        client = TestClient(app)

        response = client.get("/api/rates?symbols=12345")
        assert response.status_code == 400
        assert isinstance(response.json(), list)
