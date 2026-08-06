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


@patch("vatcomply.api._get_vat_client")
@patch("vatcomply.api.asyncio.sleep", new_callable=AsyncMock)
def test_vat_transient_fault_returns_503(mock_sleep, mock_get_client, client):
    """MS_MAX_CONCURRENT_REQ is a VIES capacity issue — 503, not 400/error."""
    from zeep.exceptions import Fault

    mock_client = MagicMock()
    mock_client.service.checkVat = AsyncMock(
        side_effect=Fault("MS_MAX_CONCURRENT_REQ")
    )
    mock_get_client.return_value = mock_client

    response = client.get("/vat?vat_number=FR35820010783")
    assert response.status_code == 503
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data
    assert "MS_MAX_CONCURRENT_REQ" in str(data["detail"])
    # Retried with backoff before giving up
    assert mock_sleep.await_count == 2
    assert mock_client.service.checkVat.await_count == 3


@patch("vatcomply.api._get_vat_client")
@patch("vatcomply.api.asyncio.sleep", new_callable=AsyncMock)
def test_vat_transient_fault_retries_then_succeeds(mock_sleep, mock_get_client, client):
    """Transient VIES fault should retry and return 200 when capacity frees."""
    from zeep.exceptions import Fault

    mock_client = MagicMock()
    mock_client.service.checkVat = AsyncMock(
        side_effect=[
            Fault("MS_MAX_CONCURRENT_REQ"),
            {
                "valid": True,
                "vatNumber": "35820010783",
                "countryCode": "FR",
                "name": "Test",
                "address": "Address",
            },
        ]
    )
    mock_get_client.return_value = mock_client

    response = client.get("/vat?vat_number=FR35820010783")
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert mock_sleep.await_count == 1
    assert mock_client.service.checkVat.await_count == 2


@patch("vatcomply.api._get_vat_client")
@patch("vatcomply.api.asyncio.sleep", new_callable=AsyncMock)
def test_vat_client_fault_does_not_retry(mock_sleep, mock_get_client, client):
    """INVALID_INPUT is permanent — do not retry."""
    from zeep.exceptions import Fault

    mock_client = MagicMock()
    mock_client.service.checkVat = AsyncMock(side_effect=Fault("INVALID_INPUT"))
    mock_get_client.return_value = mock_client

    response = client.get("/vat?vat_number=DE123456789")
    assert response.status_code == 400
    assert mock_sleep.await_count == 0
    assert mock_client.service.checkVat.await_count == 1


def test_sentry_drops_vies_max_concurrent_events():
    """before_send must drop MS_MAX_CONCURRENT_REQ so Sentry never opens VATCOMPLY-6S."""
    from vatcomply.settings import before_send

    event = {
        "message": "VIES SOAP fault for VAT FR35820010783: MS_MAX_CONCURRENT_REQ",
        "logentry": {
            "message": "VIES SOAP fault for VAT %s: %s",
            "params": ["FR35820010783", "MS_MAX_CONCURRENT_REQ"],
        },
    }
    assert before_send(event, {}) is None

    ok_event = {"message": "Scheduled command load_rates failed"}
    assert before_send(ok_event, {}) is ok_event


def test_non_field_validation_error(client):
    response = client.get("/vat")  # Missing required field
    assert response.status_code == 422
    assert isinstance(response.json(), dict)
