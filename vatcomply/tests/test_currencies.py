from vatcomply.constants import CurrencySymbol


def test_currencies_api(client):
    response = client.get("/currencies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert len(data) == len(CurrencySymbol.choices)


def test_currencies_have_name_and_symbol(client):
    response = client.get("/currencies")
    data = response.json()
    for symbol, info in data.items():
        assert "name" in info
        assert "symbol" in info
        assert info["symbol"] == symbol


def test_search_by_currency_code(client):
    response = client.get("/currencies?search=USD")
    assert response.status_code == 200
    data = response.json()
    assert "USD" in data
    for code in data:
        assert "USD" in code.upper()


def test_search_by_currency_name(client):
    response = client.get("/currencies?search=dollar")
    assert response.status_code == 200
    data = response.json()
    assert "USD" in data
    for info in data.values():
        assert "dollar" in info["name"].lower()


def test_search_case_insensitive(client):
    response_lower = client.get("/currencies?search=usd")
    response_upper = client.get("/currencies?search=USD")
    assert response_lower.json() == response_upper.json()


def test_search_no_results(client):
    response = client.get("/currencies?search=zzzzzzz")
    assert response.status_code == 200
    data = response.json()
    assert data == {}


def test_metadata_fields_present(client):
    response = client.get("/currencies?search=USD")
    data = response.json()
    usd = data["USD"]
    expected_fields = [
        "name", "symbol", "numeric_code", "currency_symbol",
        "currency_symbol_narrow", "decimal_places", "rounding",
        "countries", "official_countries", "historical",
    ]
    for field in expected_fields:
        assert field in usd, f"Missing field: {field}"


def test_decimal_places_usd(client):
    response = client.get("/currencies?search=USD")
    usd = response.json()["USD"]
    assert usd["decimal_places"] == 2


def test_decimal_places_jpy(client):
    response = client.get("/currencies?search=JPY")
    jpy = response.json()["JPY"]
    assert jpy["decimal_places"] == 0


def test_countries_non_empty_for_major_currencies(client):
    response = client.get("/currencies")
    data = response.json()
    assert len(data["USD"]["countries"]) > 0
    assert len(data["EUR"]["countries"]) > 0


def test_historical_hrk(client):
    response = client.get("/currencies?search=HRK")
    hrk = response.json()["HRK"]
    assert hrk["historical"]


def test_non_historical_usd(client):
    response = client.get("/currencies?search=USD")
    usd = response.json()["USD"]
    assert not usd["historical"]


def test_currency_symbol_values(client):
    response = client.get("/currencies")
    data = response.json()
    assert data["USD"]["currency_symbol"] == "$"
    assert data["EUR"]["currency_symbol"] == "\u20ac"


def test_numeric_code(client):
    response = client.get("/currencies?search=USD")
    usd = response.json()["USD"]
    assert usd["numeric_code"] == "840"
