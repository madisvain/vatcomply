import re

from datetime import date as dtdate
from typing import Optional

from django.conf import settings
from pydantic import BaseModel, field_validator


class VATValidationModel(BaseModel):
    vat_number: str

    @field_validator("vat_number")
    def format_validation(cls, vat_number):
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


class RatesQueryValidationModel(BaseModel):
    base: str = "EUR"
    date: Optional[dtdate] = dtdate.today()
    symbols: Optional[list] = []

    @field_validator("base")
    @classmethod
    def base_validation(cls, base: str):
        if base not in list(settings.CURRENCY_SYMBOLS):
            raise ValueError(f"Base currency {base} is not supported.")
        return base

    @field_validator("symbols", mode="before")
    @classmethod
    def symbols_validation(cls, symbols: list):
        symbols = symbols.split(",")
        diff = list(set(symbols) - set(list(settings.CURRENCY_SYMBOLS)))
        if diff:
            raise ValueError(f"Symbols {', '.join(diff)} are not supported.")
        return symbols
