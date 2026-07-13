from unittest.mock import MagicMock, patch

import httpx
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from vatcomply.models import Rate
from vatcomply.tests.fixtures import MOCK_RATES_XML

EMPTY_RATES_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
    <gesmes:subject>Reference rates</gesmes:subject>
    <gesmes:Sender><gesmes:name>European Central Bank</gesmes:name></gesmes:Sender>
    <Cube></Cube>
</gesmes:Envelope>
"""


@pytest.mark.django_db(transaction=True)
def test_load_rates_happy_path():
    Rate.objects.all().delete()
    mock_response = MagicMock()
    mock_response.content = MOCK_RATES_XML
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=mock_response):
        call_command("load_rates")

    assert Rate.objects.filter(date="2018-10-12").exists()
    assert Rate.objects.filter(date="2024-01-05").exists()
    assert Rate.objects.count() == 4


@pytest.mark.django_db(transaction=True)
def test_load_rates_http_error_raises():
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "boom",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    )
    with patch("httpx.get", return_value=mock_response):
        with pytest.raises(CommandError, match="Failed to fetch rates data"):
            call_command("load_rates")


@pytest.mark.django_db(transaction=True)
def test_load_rates_network_error_raises():
    with patch("httpx.get", side_effect=httpx.ConnectError("unreachable")):
        with pytest.raises(CommandError, match="Failed to fetch rates data"):
            call_command("load_rates")


@pytest.mark.django_db(transaction=True)
def test_load_rates_empty_xml_raises():
    mock_response = MagicMock()
    mock_response.content = EMPTY_RATES_XML
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=mock_response):
        with pytest.raises(CommandError, match="no rate cubes"):
            call_command("load_rates")


@pytest.mark.django_db(transaction=True)
def test_load_rates_invalid_xml_raises():
    mock_response = MagicMock()
    mock_response.content = b"not xml"
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=mock_response):
        with pytest.raises(CommandError, match="Failed to parse"):
            call_command("load_rates")
