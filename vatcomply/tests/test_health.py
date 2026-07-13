from datetime import date, timedelta

import pytest

from vatcomply.models import Rate


@pytest.mark.django_db(transaction=True)
def test_health_liveness(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db(transaction=True)
def test_ready_healthy_with_fresh_rates(client, settings):
    Rate.objects.all().delete()
    Rate.objects.create(date=date.today(), rates={"USD": 1.1})

    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["checks"]["check_database"]["healthy"] is True
    assert data["checks"]["check_rates_freshness"]["healthy"] is True


@pytest.mark.django_db(transaction=True)
def test_ready_unhealthy_when_rates_stale(client, settings):
    settings.RATES_MAX_AGE_DAYS = 4
    Rate.objects.all().delete()
    Rate.objects.create(
        date=date.today() - timedelta(days=10),
        rates={"USD": 1.1},
    )

    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["check_rates_freshness"]["healthy"] is False
    assert "stale" in data["checks"]["check_rates_freshness"]["message"].lower()


@pytest.mark.django_db(transaction=True)
def test_ready_unhealthy_when_no_rates(client):
    Rate.objects.all().delete()

    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["check_rates_freshness"]["healthy"] is False
