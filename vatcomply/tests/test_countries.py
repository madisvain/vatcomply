import pytest

from vatcomply.models import Country


@pytest.mark.django_db(transaction=True)
def test_countries_api(client, countries_db):
    response = client.get("/countries")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == Country.objects.count()


# --- search ---


@pytest.mark.django_db(transaction=True)
def test_search_by_name(client, countries_db):
    response = client.get("/countries?search=Estonia")
    data = response.json()
    assert response.status_code == 200
    assert any(c["name"] == "Estonia" for c in data)


@pytest.mark.django_db(transaction=True)
def test_search_by_iso2(client, countries_db):
    response = client.get("/countries?search=EE")
    data = response.json()
    assert any(c["iso2"] == "EE" for c in data)


@pytest.mark.django_db(transaction=True)
def test_search_by_iso3(client, countries_db):
    response = client.get("/countries?search=EST")
    data = response.json()
    assert any(c["iso3"] == "EST" for c in data)


@pytest.mark.django_db(transaction=True)
def test_search_case_insensitive(client, countries_db):
    response = client.get("/countries?search=estonia")
    data = response.json()
    assert any(c["name"] == "Estonia" for c in data)


@pytest.mark.django_db(transaction=True)
def test_search_no_results(client, countries_db):
    response = client.get("/countries?search=ZZZZNOTACOUNTRY")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 0


# --- region ---


@pytest.mark.django_db(transaction=True)
def test_filter_by_region(client, countries_db):
    response = client.get("/countries?region=Europe")
    data = response.json()
    assert response.status_code == 200
    assert len(data) > 0
    assert all(c["region"] == "Europe" for c in data)


@pytest.mark.django_db(transaction=True)
def test_filter_by_region_case_insensitive(client, countries_db):
    response = client.get("/countries?region=europe")
    data = response.json()
    assert len(data) > 0
    assert all(c["region"] == "Europe" for c in data)


@pytest.mark.django_db(transaction=True)
def test_filter_by_region_no_results(client, countries_db):
    response = client.get("/countries?region=Atlantis")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 0


# --- subregion ---


@pytest.mark.django_db(transaction=True)
def test_filter_by_subregion(client, countries_db):
    response = client.get("/countries?subregion=Northern Europe")
    data = response.json()
    assert response.status_code == 200
    assert len(data) > 0
    assert all(c["subregion"] == "Northern Europe" for c in data)


@pytest.mark.django_db(transaction=True)
def test_filter_by_subregion_case_insensitive(client, countries_db):
    response = client.get("/countries?subregion=northern europe")
    data = response.json()
    assert len(data) > 0
    assert all(c["subregion"] == "Northern Europe" for c in data)


# --- currency ---


@pytest.mark.django_db(transaction=True)
def test_filter_by_currency(client, countries_db):
    response = client.get("/countries?currency=EUR")
    data = response.json()
    assert response.status_code == 200
    assert len(data) > 0
    assert all(c["currency"] == "EUR" for c in data)


@pytest.mark.django_db(transaction=True)
def test_filter_by_currency_case_insensitive(client, countries_db):
    response = client.get("/countries?currency=eur")
    data = response.json()
    assert len(data) > 0
    assert all(c["currency"] == "EUR" for c in data)


@pytest.mark.django_db(transaction=True)
def test_filter_by_currency_no_results(client, countries_db):
    response = client.get("/countries?currency=ZZZCUR")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 0


# --- combined filters ---


@pytest.mark.django_db(transaction=True)
def test_combined_region_and_currency(client, countries_db):
    response = client.get("/countries?region=Europe&currency=EUR")
    data = response.json()
    assert response.status_code == 200
    assert len(data) > 0
    assert all(c["region"] == "Europe" and c["currency"] == "EUR" for c in data)


@pytest.mark.django_db(transaction=True)
def test_combined_search_and_region(client, countries_db):
    response = client.get("/countries?search=land&region=Europe")
    data = response.json()
    assert response.status_code == 200
    assert all(c["region"] == "Europe" for c in data)


@pytest.mark.django_db(transaction=True)
def test_combined_filters_no_results(client, countries_db):
    response = client.get("/countries?region=Europe&currency=USD")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 0
