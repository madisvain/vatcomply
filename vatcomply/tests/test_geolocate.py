import pytest

from vatcomply.models import Country


@pytest.mark.django_db(transaction=True)
def test_geolocate_without_headers(client, countries_db):
    """Test geolocate endpoint without required CDN headers"""
    response = client.get("/geolocate")
    assert response.status_code == 404
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data
    assert (
        data["detail"]
        == "Country code not received from CDN headers (CF-IPCountry or Cdn-RequestCountryCode)."
    )


@pytest.mark.django_db(transaction=True)
def test_geolocate_with_invalid_country(client, countries_db):
    """Test geolocate endpoint with invalid country code"""
    response = client.get(
        "/geolocate",
        headers={
            "cf-ipcountry": "XX",  # Invalid country code
            "cf-connecting-ip": "1.2.3.4",
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data
    assert data["detail"] == "Data for country code `XX` not found."


@pytest.mark.django_db(transaction=True)
def test_geolocate_success(client, countries_db):
    """Test successful geolocate endpoint call"""
    response = client.get(
        "/geolocate",
        headers={
            "cf-ipcountry": "DE",
            "cf-connecting-ip": "85.214.132.117",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

    country = Country.objects.get(iso2="DE")

    assert data["country_code"] == "DE"
    assert data["iso2"] == country.iso2
    assert data["iso3"] == country.iso3
    assert data["name"] == country.name
    assert data["numeric_code"] == country.numeric_code
    assert data["phone_code"] == country.phone_code
    assert data["capital"] == country.capital
    assert data["currency"] == country.currency
    assert data["tld"] == country.tld
    assert data["region"] == country.region
    assert data["subregion"] == country.subregion
    assert data["latitude"] == country.latitude
    assert data["longitude"] == country.longitude
    assert data["emoji"] == country.emoji
    assert data["ip"] == "85.214.132.117"


@pytest.mark.django_db(transaction=True)
def test_geolocate_with_bunny_header(client, countries_db):
    """Test geolocate endpoint with Bunny.net CDN header"""
    response = client.get(
        "/geolocate",
        headers={
            "cdn-requestcountrycode": "FR",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

    country = Country.objects.get(iso2="FR")

    assert data["country_code"] == "FR"
    assert data["iso2"] == country.iso2
    assert data["name"] == country.name
