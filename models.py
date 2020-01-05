from datetime import date
from typing import Optional

from passlib.hash import pbkdf2_sha256
from pydantic import BaseModel, ValidationError, validator, root_validator, EmailStr, SecretStr
from pydantic.dataclasses import dataclass

from db import database, Users
from settings import SYMBOLS


class LoginValidationModel(BaseModel):
    email: EmailStr
    password: SecretStr

    @root_validator
    def password_length(cls, values):
        email, password = values.get("email"), values.get("password")
        user = database.fetch_one(query=Users.select().where(Users.c.email == email))
        if not user or pbkdf2_sha256.verify(password.get_secret_value(), user.password):
            raise ValueError(
                "Please enter a correct username and password. Note that both fields may be case-sensitive."
            )
        return values


class RatesQueryValidationModel(BaseModel):
    base: str = "EUR"
    date: Optional[date]
    symbols: Optional[list]

    @validator("base")
    def base_validation(cls, base):
        if base not in list(SYMBOLS):
            raise ValueError(f"Base currency {base} is not supported.")
        return base

    @validator("symbols", pre=True, whole=True)
    def symbols_validation(cls, symbols):
        symbols = symbols.split(",")
        diff = list(set(symbols) - set(list(SYMBOLS)))
        if diff:
            raise ValueError(f"Symbols {', '.join(diff)} are not supported.")
        return symbols


class RegistrationValidationModel(BaseModel):
    email: EmailStr
    password: SecretStr

    @validator("email")
    def unique_email(cls, v):
        user = database.fetch_one(query=Users.select().where(Users.c.email == v))
        if user:
            raise ValueError("A user with this email already exists.")
        return v

    @validator("password")
    def password_length(cls, v):
        if len(v.get_secret_value()) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return v


class VATValidationModel(BaseModel):
    vat_number: str

    @validator("vat_number")
    def format_validation(cls, v):
        # TODO: implement Regex validators
        return v
