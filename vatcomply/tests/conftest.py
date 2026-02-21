"""Shared pytest fixtures for VATcomply tests."""

from unittest.mock import patch, MagicMock

import pytest
from django.conf import settings
from django.core.management import call_command
from django_bolt.testing import TestClient

# Disable rate limiting during tests (must be set before api module import)
settings.THROTTLE = False

from vatcomply.api import api
from vatcomply.models import Country, Rate
from vatcomply.tests.fixtures import MOCK_COUNTRIES_JSON, MOCK_RATES_XML


@pytest.fixture
def client():
    with TestClient(api) as c:
        yield c


def _mock_load_countries():
    """Load countries from fixture instead of hitting the network."""
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_COUNTRIES_JSON
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=mock_response):
        call_command("load_countries")


def _mock_load_rates():
    """Load rates from fixture instead of hitting ECB."""
    mock_response = MagicMock()
    mock_response.content = MOCK_RATES_XML
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=mock_response):
        call_command("load_rates")


@pytest.fixture
def countries_db(transactional_db):
    Country.objects.all().delete()
    _mock_load_countries()
    yield
    Country.objects.all().delete()


@pytest.fixture
def rates_db(transactional_db):
    Rate.objects.all().delete()
    _mock_load_rates()
    yield
    Rate.objects.all().delete()
