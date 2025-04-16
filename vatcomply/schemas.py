import re
from ninja import Schema
from pydantic import BaseModel, field_validator
from decimal import Decimal
from typing import Optional, Dict
from datetime import date as datetime_date
from schwifty import IBAN

from vatcomply.constants import CurrencySymbol

CURRENCY_SYMBOLS = [choice[0] for choice in CurrencySymbol.choices]


class RootResponseSchema(BaseModel):
    name: str
    version: str
    status: str
    description: str
    documentation: str
    endpoints: Dict[str, str]
    contact: str


class CountrySchema(BaseModel):
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
    latitude: Decimal
    longitude: Decimal
    emoji: str


class CurrencySchema(BaseModel):
    name: str
    symbol: CurrencySymbol


class GeolocateResponse(BaseModel):
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
    ip: Optional[str]


"""
IBAN
"""


class IBANQueryParamsSchema(BaseModel):
    iban: IBAN


class ValidateIBANResponseSchema(BaseModel):
    valid: bool
    iban: IBAN
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


"""
VAT
"""


class VATQueryParamsSchema(BaseModel):
    vat_number: str

    @field_validator("vat_number")
    @classmethod
    def vat_number_validation(cls, vat_number: str):
        pattern = r"^[A-Z]{2}[\dA-Z]{8,12}$"
        if not re.match(pattern, vat_number):
            raise ValueError(
                "Invalid VAT number format. Expected format: Two-letter country code followed by 8-12 digits or letters."
            )

        # Brexit
        if vat_number.startswith("GB"):
            raise ValueError(
                "As of 01/01/2021, the VoW service to validate UK (GB) VAT numbers ceased to exist while a new service to validate VAT numbers of businesses operating under the Protocol on Ireland and Northern Ireland appeared. These VAT numbers are starting with the “XI” prefix."
            )
        return vat_number


class ValidateVATResponseSchema(BaseModel):
    valid: bool
    vat_number: str
    name: Optional[str] = None
    address: str = ""
    country_code: str


"""
Rates
"""


class RatesQueryParamsSchema(Schema):
    base: Optional[str] = "EUR"
    symbols: Optional[str] = None
    date: Optional[datetime_date] = None

    @field_validator("base")
    @classmethod
    def base_validation(cls, base: str):
        if base not in CURRENCY_SYMBOLS:
            raise ValueError(f"Base currency {base} is not supported.")
        return base

    @field_validator("symbols")
    @classmethod
    def split_symbols(cls, value):
        if isinstance(value, str):
            symbols = value.split(",")
            for symbol in symbols:
                if symbol not in CURRENCY_SYMBOLS:
                    raise ValueError(f"Currency {symbol} is not supported.")
            return symbols
        return value


class RatesResponseSchema(BaseModel):
    date: str
    base: CurrencySymbol
    rates: Dict[str, float]


"""
Errors
"""


class ErrorResponse(BaseModel):
    error: str
