"""
Response schemas for VATcomply API.

Uses Django Bolt's Serializer for model integration and high-performance serialization.
"""

from django_bolt.serializers import Serializer


class RootResponseSchema(Serializer):
    """Root API information response."""

    name: str
    version: str
    status: str
    description: str
    documentation: str
    endpoints: dict[str, str]
    contact: str


class CountrySchema(Serializer):
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
    latitude: float
    longitude: float
    emoji: str


class CurrencySchema(Serializer):
    """Currency information response."""

    name: str
    symbol: str
    numeric_code: str = ""
    currency_symbol: str = ""
    currency_symbol_narrow: str | None = None
    decimal_places: int = 2
    rounding: int = 0
    countries: list[str] = []


class GeolocateResponse(Serializer):
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
    ip: str | None = None


class ValidateIBANResponseSchema(Serializer):
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


class ValidateVATResponseSchema(Serializer):
    """VAT validation response."""

    valid: bool
    vat_number: str
    country_code: str
    name: str | None = None
    address: str = ""


class VATRateSchema(Serializer):
    """EU VAT rate response."""

    country_code: str
    country_name: str
    standard_rate: float
    reduced_rates: list[float]
    super_reduced_rate: float | None = None
    parking_rate: float | None = None
    currency: str = ""
    member_state: bool = True
    rate_comments: dict[str, list[str]] = {}


class RatesResponseSchema(Serializer):
    """Exchange rates response."""

    date: str
    base: str
    rates: dict[str, float]
