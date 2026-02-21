"""
Response schemas for VATcomply API.

Uses msgspec.Struct for high-performance serialization with Django Bolt.
Validation logic has been moved to the API endpoints.
"""

import msgspec
from typing import Optional


class RootResponseSchema(msgspec.Struct):
    """Root API information response."""

    name: str
    version: str
    status: str
    description: str
    documentation: str
    endpoints: dict[str, str]
    contact: str


class CountrySchema(msgspec.Struct):
    """Country details response."""

    iso2: str
    iso3: str
    name: str
    numeric_code: int
    phone_code: str
    capital: str
    currency: str
    tld: str
    region: str
    subregion: str
    latitude: float  # msgspec uses float instead of Decimal
    longitude: float
    emoji: str


class CurrencySchema(msgspec.Struct):
    """Currency information response."""

    name: str
    symbol: str
    numeric_code: str = ""
    currency_symbol: str = ""
    currency_symbol_narrow: Optional[str] = None
    decimal_places: int = 2
    rounding: int = 0
    countries: list[str] = []
    official_countries: list[str] = []
    historical: bool = False


class GeolocateResponse(msgspec.Struct):
    """IP geolocation response."""

    iso2: str
    iso3: str
    country_code: str
    name: str
    numeric_code: int
    phone_code: str
    capital: str
    currency: str
    tld: str
    region: str
    subregion: str
    latitude: float
    longitude: float
    emoji: str
    ip: Optional[str] = None


class ValidateIBANResponseSchema(msgspec.Struct):
    """IBAN validation response."""

    valid: bool
    iban: str
    bank_name: str
    bic: str
    country_code: str
    country_name: str
    checksum_digits: str
    bank_code: str
    branch_code: str
    account_number: str
    bban: str
    in_sepa_zone: bool


class ValidateVATResponseSchema(msgspec.Struct):
    """VAT validation response."""

    valid: bool
    vat_number: str
    country_code: str
    name: Optional[str] = None
    address: str = ""


class RatesResponseSchema(msgspec.Struct):
    """Exchange rates response."""

    date: str
    base: str
    rates: dict[str, float]
