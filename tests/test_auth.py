from starlette.testclient import TestClient

from app import app


class TestCurrenciesAPI(object):
    def test_auth(self):
        with TestClient(app) as client:
            response = client.get("/api/register")
            assert response.status_code == 405

    def test_register(self):
        with TestClient(app) as client:
            response = client.post("/api/register", json={"email": "test@test.com", "password": "password"})
            assert response.status_code == 201
