from datetime import date
from typing import Optional

from pydantic import BaseModel, ValidationError, validator
from pydantic.dataclasses import dataclass
from starlette.config import Config
from starlette.datastructures import CommaSeparatedStrings

config = Config(".env")


class RatesQueryValidationModel(BaseModel):
    base: str = "EUR"
    date: Optional[date]
    symbols: Optional[list]

    @validator("base")
    def base_validation(cls, base):
        if base not in config("SYMBOLS", CommaSeparatedStrings):
            raise ValueError(f"Base currency {base} is not supported.")
        return base

    @validator("symbols", pre=True, whole=True)
    def symbols_validation(cls, symbols):
        symbols = symbols.split(",")
        diff = list(set(symbols) - set(config("SYMBOLS", CommaSeparatedStrings)))
        if diff:
            raise ValueError(f"Symbols {', '.join(diff)} are not supported.")
        return symbols


class VATValidationModel(BaseModel):
    vat_number: str

    @validator("vat_number")
    def format_validation(cls, v):
        # TODO: implement Regex validators
        return v