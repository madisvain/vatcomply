from starlette.testclient import TestClient

from app import app


class TestVATAPI(object):
    def test_vat_api(self):
        with TestClient(app) as client:
            response = client.get("/api/vat", headers={"Authorization": "Token test-token"})
            assert response.status_code == 200
            # assert isinstance(response.json(), dict)
