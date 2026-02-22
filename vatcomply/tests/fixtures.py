"""Test fixtures for VATcomply tests. Avoids network calls to ECB, GitHub, and TEDB."""

MOCK_COUNTRIES_JSON = [
    {
        "iso2": "EE",
        "iso3": "EST",
        "name": "Estonia",
        "numeric_code": "233",
        "phonecode": "372",
        "capital": "Tallinn",
        "currency": "EUR",
        "tld": ".ee",
        "region": "Europe",
        "subregion": "Northern Europe",
        "latitude": "59.0",
        "longitude": "26.0",
        "emoji": "\U0001f1ea\U0001f1ea",
    },
    {
        "iso2": "FI",
        "iso3": "FIN",
        "name": "Finland",
        "numeric_code": "246",
        "phonecode": "358",
        "capital": "Helsinki",
        "currency": "EUR",
        "tld": ".fi",
        "region": "Europe",
        "subregion": "Northern Europe",
        "latitude": "64.0",
        "longitude": "26.0",
        "emoji": "\U0001f1eb\U0001f1ee",
    },
    {
        "iso2": "DE",
        "iso3": "DEU",
        "name": "Germany",
        "numeric_code": "276",
        "phonecode": "49",
        "capital": "Berlin",
        "currency": "EUR",
        "tld": ".de",
        "region": "Europe",
        "subregion": "Western Europe",
        "latitude": "51.0",
        "longitude": "9.0",
        "emoji": "\U0001f1e9\U0001f1ea",
    },
    {
        "iso2": "IS",
        "iso3": "ISL",
        "name": "Iceland",
        "numeric_code": "352",
        "phonecode": "354",
        "capital": "Reykjavik",
        "currency": "ISK",
        "tld": ".is",
        "region": "Europe",
        "subregion": "Northern Europe",
        "latitude": "65.0",
        "longitude": "-18.0",
        "emoji": "\U0001f1ee\U0001f1f8",
    },
    {
        "iso2": "FR",
        "iso3": "FRA",
        "name": "France",
        "numeric_code": "250",
        "phonecode": "33",
        "capital": "Paris",
        "currency": "EUR",
        "tld": ".fr",
        "region": "Europe",
        "subregion": "Western Europe",
        "latitude": "46.0",
        "longitude": "2.0",
        "emoji": "\U0001f1eb\U0001f1f7",
    },
    {
        "iso2": "US",
        "iso3": "USA",
        "name": "United States",
        "numeric_code": "840",
        "phonecode": "1",
        "capital": "Washington",
        "currency": "USD",
        "tld": ".us",
        "region": "Americas",
        "subregion": "Northern America",
        "latitude": "38.0",
        "longitude": "-97.0",
        "emoji": "\U0001f1fa\U0001f1f8",
    },
    {
        "iso2": "JP",
        "iso3": "JPN",
        "name": "Japan",
        "numeric_code": "392",
        "phonecode": "81",
        "capital": "Tokyo",
        "currency": "JPY",
        "tld": ".jp",
        "region": "Asia",
        "subregion": "Eastern Asia",
        "latitude": "36.0",
        "longitude": "138.0",
        "emoji": "\U0001f1ef\U0001f1f5",
    },
]

MOCK_VAT_RATES_RESPONSE = {
    "additionalInformation": {
        "countries": {
            "country": [
                {"isoCode": "DE", "cnCodeProvided": False, "cpaCodeProvided": False},
                {"isoCode": "FR", "cnCodeProvided": False, "cpaCodeProvided": False},
                {"isoCode": "EE", "cnCodeProvided": False, "cpaCodeProvided": False},
            ]
        }
    },
    "vatRateResults": [
        {
            "memberState": "DE",
            "type": "STANDARD",
            "rate": {"type": "DEFAULT", "value": 19.0},
            "situationOn": "2024-01-05",
        },
        {
            "memberState": "DE",
            "type": "REDUCED",
            "rate": {"type": "REDUCED_RATE", "value": 7.0},
            "situationOn": "2024-01-05",
        },
        {
            "memberState": "FR",
            "type": "STANDARD",
            "rate": {"type": "DEFAULT", "value": 20.0},
            "situationOn": "2024-01-05",
        },
        {
            "memberState": "FR",
            "type": "REDUCED",
            "rate": {"type": "REDUCED_RATE", "value": 5.5},
            "situationOn": "2024-01-05",
        },
        {
            "memberState": "FR",
            "type": "REDUCED",
            "rate": {"type": "REDUCED_RATE", "value": 10.0},
            "situationOn": "2024-01-05",
        },
        {
            "memberState": "FR",
            "type": "REDUCED",
            "rate": {"type": "SUPER_REDUCED_RATE", "value": 2.1},
            "situationOn": "2024-01-05",
        },
        {
            "memberState": "EE",
            "type": "STANDARD",
            "rate": {"type": "DEFAULT", "value": 22.0},
            "situationOn": "2024-01-05",
        },
        {
            "memberState": "EE",
            "type": "REDUCED",
            "rate": {"type": "REDUCED_RATE", "value": 9.0},
            "situationOn": "2024-01-05",
        },
    ],
}

MOCK_RATES_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
    <gesmes:subject>Reference rates</gesmes:subject>
    <gesmes:Sender><gesmes:name>European Central Bank</gesmes:name></gesmes:Sender>
    <Cube>
        <Cube time="2024-01-05">
            <Cube currency="USD" rate="1.0943"/>
            <Cube currency="JPY" rate="159.14"/>
            <Cube currency="GBP" rate="0.86068"/>
            <Cube currency="CHF" rate="0.9307"/>
            <Cube currency="SEK" rate="11.1955"/>
        </Cube>
        <Cube time="2024-01-04">
            <Cube currency="USD" rate="1.0956"/>
            <Cube currency="JPY" rate="158.83"/>
            <Cube currency="GBP" rate="0.86270"/>
            <Cube currency="CHF" rate="0.9317"/>
            <Cube currency="SEK" rate="11.2010"/>
        </Cube>
        <Cube time="2018-10-12">
            <Cube currency="USD" rate="1.1563"/>
            <Cube currency="JPY" rate="130.07"/>
            <Cube currency="GBP" rate="0.87700"/>
            <Cube currency="CHF" rate="1.1427"/>
            <Cube currency="SEK" rate="10.3183"/>
        </Cube>
        <Cube time="2018-10-11">
            <Cube currency="USD" rate="1.1536"/>
            <Cube currency="JPY" rate="129.59"/>
            <Cube currency="GBP" rate="0.87700"/>
            <Cube currency="CHF" rate="1.1399"/>
            <Cube currency="SEK" rate="10.3260"/>
        </Cube>
    </Cube>
</gesmes:Envelope>
"""
