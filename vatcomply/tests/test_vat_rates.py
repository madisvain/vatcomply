import pytest


@pytest.mark.django_db(transaction=True)
def test_vat_rates_list(client, vat_rates_db):
    response = client.get("/vat_rates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4
    codes = [r["country_code"] for r in data]
    assert "AT" in codes
    assert "DE" in codes
    assert "FR" in codes
    assert "EE" in codes


@pytest.mark.django_db(transaction=True)
def test_vat_rates_filter_country(client, vat_rates_db):
    response = client.get("/vat_rates?country_code=DE")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["country_code"] == "DE"
    assert data[0]["standard_rate"] == 19.0
    assert data[0]["reduced_rates"] == [7.0]
    assert data[0]["country_name"] == "Germany"
    assert data[0]["member_state"] is True


@pytest.mark.django_db(transaction=True)
def test_vat_rates_filter_case_insensitive(client, vat_rates_db):
    response = client.get("/vat_rates?country_code=de")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["country_code"] == "DE"


@pytest.mark.django_db(transaction=True)
def test_vat_rates_filter_invalid_code(client, vat_rates_db):
    response = client.get("/vat_rates?country_code=ZZ")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@pytest.mark.django_db(transaction=True)
def test_vat_rates_france_multiple_reduced(client, vat_rates_db):
    response = client.get("/vat_rates?country_code=FR")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    fr = data[0]
    assert fr["standard_rate"] == 20.0
    assert fr["reduced_rates"] == [5.5, 10.0]
    assert fr["super_reduced_rate"] == 2.1


@pytest.mark.django_db(transaction=True)
def test_vat_rates_response_fields(client, vat_rates_db):
    response = client.get("/vat_rates?country_code=EE")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    ee = data[0]
    expected_fields = {
        "country_code", "country_name", "standard_rate", "reduced_rates",
        "super_reduced_rate", "parking_rate", "currency", "member_state",
        "rate_comments",
    }
    assert set(ee.keys()) == expected_fields
    assert ee["country_code"] == "EE"
    assert ee["country_name"] == "Estonia"
    assert ee["standard_rate"] == 22.0
    assert ee["reduced_rates"] == [9.0]
    assert ee["super_reduced_rate"] is None
    assert ee["parking_rate"] is None
    assert ee["currency"] == "EUR"
    assert ee["member_state"] is True
    assert ee["rate_comments"] == {}


@pytest.mark.django_db(transaction=True)
def test_vat_rates_austria_rate_comments(client, vat_rates_db):
    response = client.get("/vat_rates?country_code=AT")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    at = data[0]
    assert at["standard_rate"] == 20.0
    assert 19.0 in at["reduced_rates"]
    assert at["rate_comments"]["19.0"] == "Jungholz, Mittelberg"
    assert at["parking_rate"] == 13.0


@pytest.mark.django_db(transaction=True)
def test_vat_rates_no_comments_empty_dict(client, vat_rates_db):
    response = client.get("/vat_rates?country_code=FR")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["rate_comments"] == {}
