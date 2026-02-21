# Known-good IBAN for deterministic tests
TEST_IBAN = "DE89370400440532013000"


def test_iban_api(client):
    response = client.get(f"/iban?iban={TEST_IBAN}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["valid"]
    assert data["country_code"] == "DE"
    assert "bban" in data
    assert "bank_code" in data


def test_iban_blank_api(client):
    response = client.get("/iban?iban=")
    assert response.status_code == 400
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data


def test_iban_invalid_format_api(client):
    response = client.get("/iban?iban=123")
    assert response.status_code == 400
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data


def test_iban_invalid_checksum(client):
    response = client.get("/iban?iban=DE89370400440532013")
    assert response.status_code == 400
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data


def test_non_field_validation_error(client):
    response = client.get("/iban")  # Missing required field
    assert response.status_code == 422
    assert isinstance(response.json(), dict)
