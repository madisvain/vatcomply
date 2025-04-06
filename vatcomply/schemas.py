from ninja import Schema
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Optional
from datetime import date


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
    symbol: str


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


class ErrorResponse(BaseModel):
    error: str


class VATValidationModel(BaseModel):
    vat_number: str = Field(..., pattern=r"^[A-Z]{2}[A-Z0-9]+$")


class RatesQueryParamsSchema(Schema):
    base: Optional[str] = "EUR"
    symbols: Optional[str] = None
    date: Optional[date] = None

    @field_validator("symbols")
    def split_symbols(cls, value):
        if isinstance(value, str):
            return value.split(",")
        return value
