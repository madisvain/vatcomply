from unittest.mock import patch, AsyncMock, MagicMock


def test_vat_blank_api(client):
    response = client.get("/vat?vat_number=")
    assert response.status_code == 400
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data


def test_vat_invalid_format_api(client):
    response = client.get("/vat?vat_number=123")
    assert response.status_code == 400
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data


def test_vat_brexit_api(client):
    response = client.get("/vat?vat_number=GB123456789")
    assert response.status_code == 400
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data
    assert "GB" in data["detail"]


@patch("vatcomply.api._get_vat_client")
def test_vat_valid_number(mock_get_client, client):
    mock_client = MagicMock()
    mock_client.service.checkVat = AsyncMock(return_value={
        "valid": True,
        "vatNumber": "101600930",
        "countryCode": "EE",
        "name": "Test Company",
        "address": "Test Address",
    })
    mock_get_client.return_value = mock_client

    response = client.get("/vat?vat_number=EE101600930")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"]
    assert data["country_code"] == "EE"
    assert data["name"] == "Test Company"


@patch("vatcomply.api._get_vat_client")
def test_vat_service_fault(mock_get_client, client):
    from zeep.exceptions import Fault
    mock_client = MagicMock()
    mock_client.service.checkVat = AsyncMock(side_effect=Fault("INVALID_INPUT"))
    mock_get_client.return_value = mock_client

    response = client.get("/vat?vat_number=DE123456789")
    assert response.status_code == 400
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data


def test_non_field_validation_error(client):
    response = client.get("/vat")  # Missing required field
    assert response.status_code == 422
    assert isinstance(response.json(), dict)
