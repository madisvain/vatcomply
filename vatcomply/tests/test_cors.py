import pytest


@pytest.mark.django_db(transaction=True)
def test_cors_header_present(client):
    """CORS Access-Control-Allow-Origin header must be set on API responses."""
    response = client.get("/", headers={"Origin": "https://example.com"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"


@pytest.mark.django_db(transaction=True)
def test_cors_preflight(client):
    """OPTIONS preflight request should return CORS headers."""
    response = client.options(
        "/",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "*"
