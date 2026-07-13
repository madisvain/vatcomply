from datetime import date, timedelta
from unittest.mock import patch

import pytest

from vatcomply.models import Rate


@pytest.mark.django_db(transaction=True)
def test_latest_api(client, rates_db):
    response = client.get("/rates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "date" in data
    assert "base" in data
    assert data["base"] == "EUR"
    assert "rates" in data
    assert len(data["rates"]) > 0
    # EUR should always be 1.0 when base is EUR
    assert data["rates"].get("EUR") == 1.0


@pytest.mark.django_db(transaction=True)
def test_date_api(client, rates_db):
    response = client.get("/rates?date=2018-10-12")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "date" in data
    assert data["date"] == "2018-10-12"
    assert "base" in data
    assert data["base"] == "EUR"
    assert "rates" in data
    assert len(data["rates"]) > 0


@pytest.mark.django_db(transaction=True)
def test_invalid_date_api(client, rates_db):
    response = client.get("/rates?date=abc")
    assert response.status_code == 400
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data


@pytest.mark.django_db(transaction=True)
def test_partial_date_rejected(client, rates_db):
    # Year-only should be rejected (not YYYY-MM-DD)
    response = client.get("/rates?date=2024")
    assert response.status_code == 400
    # Year-month should be rejected
    response = client.get("/rates?date=2024-01")
    assert response.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_invalid_calendar_date(client, rates_db):
    response = client.get("/rates?date=2024-02-30")
    assert response.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_date_weekend_api(client, rates_db):
    response = client.get("/rates?date=2018-10-13")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "date" in data
    # Weekend should fall back to Friday
    assert data["date"] == "2018-10-12"
    assert "base" in data
    assert data["base"] == "EUR"
    assert "rates" in data
    assert len(data["rates"]) > 0


@pytest.mark.django_db(transaction=True)
def test_base_api(client, rates_db):
    response = client.get("/rates?base=USD")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "date" in data
    assert "base" in data
    assert data["base"] == "USD"
    assert "rates" in data
    assert len(data["rates"]) > 0
    assert data["rates"]["USD"] == 1


@pytest.mark.django_db(transaction=True)
def test_invalid_base_currency(client, rates_db):
    response = client.get("/rates?base=INVALID")
    assert response.status_code == 400
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data


@pytest.mark.django_db(transaction=True)
def test_symbols_api(client, rates_db):
    response = client.get("/rates?symbols=USD,JPY,GBP")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "date" in data
    assert "base" in data
    assert data["base"] == "EUR"
    assert "rates" in data
    assert len(data["rates"]) == 3
    assert "USD" in data["rates"]
    assert "JPY" in data["rates"]
    assert "GBP" in data["rates"]


@pytest.mark.django_db(transaction=True)
def test_invalid_symbols_api(client, rates_db):
    response = client.get("/rates?symbols=12345")
    assert response.status_code == 400
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data


@pytest.mark.django_db(transaction=True)
def test_strict_exact_date_miss_returns_404(client, rates_db):
    # Weekend: without strict falls back to Friday; with strict must 404
    fallback = client.get("/rates?date=2018-10-13")
    assert fallback.status_code == 200
    assert fallback.json()["date"] == "2018-10-12"

    response = client.get("/rates?date=2018-10-13&strict=true")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "exact date" in data["detail"].lower()


@pytest.mark.django_db(transaction=True)
def test_strict_exact_date_hit(client, rates_db):
    response = client.get("/rates?date=2018-10-12&strict=true")
    assert response.status_code == 200
    assert response.json()["date"] == "2018-10-12"


@pytest.mark.django_db(transaction=True)
def test_strict_latest_stale_returns_503(client, settings):
    settings.RATES_MAX_AGE_DAYS = 4
    Rate.objects.all().delete()
    Rate.objects.create(
        date=date.today() - timedelta(days=10),
        rates={"USD": 1.1, "GBP": 0.8},
    )

    response = client.get("/rates?strict=true")
    assert response.status_code == 503
    data = response.json()
    assert "detail" in data
    assert "stale" in data["detail"].lower()


@pytest.mark.django_db(transaction=True)
def test_non_strict_latest_serves_stale_with_warning(client, settings):
    settings.RATES_MAX_AGE_DAYS = 4
    Rate.objects.all().delete()
    stale_date = date.today() - timedelta(days=10)
    Rate.objects.create(date=stale_date, rates={"USD": 1.1, "GBP": 0.8})

    with patch("vatcomply.api.sentry_sdk.capture_message") as capture:
        response = client.get("/rates")
    assert response.status_code == 200
    assert response.json()["date"] == stale_date.isoformat()
    capture.assert_called_once()
    assert "stale" in capture.call_args[0][0].lower()