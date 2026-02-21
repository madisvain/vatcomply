from urllib.parse import urljoin

import pytest
from django.conf import settings


@pytest.mark.django_db(transaction=True)
def test_root_endpoint(client):
    """Test the root endpoint returns correct API information"""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()

    # Check all required fields are present
    assert isinstance(data, dict)
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert "description" in data
    assert "documentation" in data
    assert "endpoints" in data
    assert "contact" in data

    # Check specific values
    assert data["name"] == "VATComply API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "operational"
    assert data["description"] == "VAT validation API, geolocation tools, and ECB exchange rates"
    assert data["documentation"] == urljoin(settings.BASE_URL, "docs")
    assert data["contact"] == "support@vatcomply.com"

    # Check endpoints
    assert isinstance(data["endpoints"], dict)
    assert len(data["endpoints"]) > 0

    # Check some known endpoints are present and properly formatted
    expected_endpoints = ["countries", "currencies", "geolocate", "vat", "rates"]
    for endpoint in expected_endpoints:
        assert endpoint in data["endpoints"]
