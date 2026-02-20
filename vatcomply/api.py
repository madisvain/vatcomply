"""
VATcomply API

Provides VAT validation, currency rates, geolocation, and IBAN validation endpoints.
"""

import contextlib
import os
import re
from decimal import Decimal
from typing import Annotated, Optional

import pendulum
import zeep
from django.conf import settings
from django_bolt import BoltAPI, Request
from django_bolt.exceptions import BadRequest, NotFound
from django_bolt.middleware import rate_limit
from django_bolt.openapi import OpenAPIConfig
from django_bolt.params import Query
from pycountry import countries as pycountries
from schwifty import IBAN
from urllib.parse import urljoin
from zeep.transports import AsyncTransport

from vatcomply.constants import CurrencySymbol
from vatcomply.error_handler import CustomErrorMiddleware
from vatcomply.models import Country, Rate
from vatcomply.schemas import (
    CountrySchema,
    CurrencySchema,
    GeolocateResponse,
    RatesResponseSchema,
    RootResponseSchema,
    ValidateIBANResponseSchema,
    ValidateVATResponseSchema,
)

# Validation constants
VAT_PATTERN = r"^[A-Z]{2}[\dA-Z]{8,12}$"
CURRENCY_SYMBOLS = [choice[0] for choice in CurrencySymbol.choices]

# Configure rate limiting based on settings
RATE_LIMIT = "2/s" if settings.THROTTLE else None

# Create the API instance
api = BoltAPI(
    middleware=[CustomErrorMiddleware],
    openapi_config=OpenAPIConfig(
        title="Vatcomply API",
        version="1.0.0",
        description="API for automated VAT compliance and currency conversion.",
    ),
)


@api.get("/countries", summary="Get list of countries")
@rate_limit(RATE_LIMIT)
async def countries(request: Request) -> list[CountrySchema]:
    """Fetches a list of countries with their details."""
    result = []
    async for country in Country.objects.order_by("iso2").all():
        result.append(
            CountrySchema(
                iso2=country.iso2,
                iso3=country.iso3,
                name=country.name,
                numeric_code=country.numeric_code,
                phone_code=country.phone_code,
                capital=country.capital,
                currency=country.currency,
                tld=country.tld,
                region=country.region,
                subregion=country.subregion,
                latitude=float(country.latitude),
                longitude=float(country.longitude),
                emoji=country.emoji,
            )
        )
    return result


@api.get("/currencies", summary="Get list of supported currencies")
@rate_limit(RATE_LIMIT)
def get_currencies(request: Request) -> dict[str, CurrencySchema]:
    """Returns all supported currencies."""
    currencies = {}
    for choice in CurrencySymbol.choices:
        symbol = choice[0]
        currencies[symbol] = CurrencySchema(
            name=choice[1],
            symbol=symbol,
        )
    return currencies


@api.get("/geolocate", summary="Geolocate by IP")
@rate_limit(RATE_LIMIT)
async def geolocate(request: Request) -> GeolocateResponse:
    """Geolocates the user based on CDN headers (Cloudflare or Bunny.net)."""
    # HTTP headers are case-insensitive; use lowercase for ASGI compatibility
    # Try Cloudflare first, then Bunny.net
    country_code = request.headers.get("cf-ipcountry") or request.headers.get(
        "cdn-requestcountrycode"
    )
    ip = request.headers.get("cf-connecting-ip")

    if not country_code:
        raise NotFound(
            detail="Country code not received from CDN headers (CF-IPCountry or Cdn-RequestCountryCode)."
        )

    try:
        record = await Country.objects.aget(iso2=country_code.upper())
    except Country.DoesNotExist:
        raise NotFound(detail=f"Data for country code `{country_code.upper()}` not found.")

    return GeolocateResponse(
        iso2=record.iso2,
        iso3=record.iso3,
        country_code=country_code.upper(),
        name=record.name,
        numeric_code=record.numeric_code,
        phone_code=record.phone_code,
        capital=record.capital,
        currency=record.currency,
        tld=record.tld,
        region=record.region,
        subregion=record.subregion,
        latitude=record.latitude,
        longitude=record.longitude,
        emoji=record.emoji,
        ip=ip,
    )


@api.get("/iban", summary="Validate IBAN")
@rate_limit(RATE_LIMIT)
def validate_iban(
    request: Request,
    iban: Annotated[str, Query(description="IBAN to validate")],
) -> ValidateIBANResponseSchema:
    """Validates an IBAN and returns details about the bank account."""
    try:
        iban_obj = IBAN(iban)
    except ValueError as e:
        raise BadRequest(detail=str(e))

    country = pycountries.get(alpha_2=iban_obj.country_code)

    return ValidateIBANResponseSchema(
        valid=True,
        iban=iban,
        bank_name=iban_obj.bank_name or "",
        bic=str(iban_obj.bic) if iban_obj.bic else "",
        country_code=iban_obj.country_code,
        country_name=country.name if country else "",
        checksum_digits=iban_obj.checksum_digits,
        bank_code=iban_obj.bank_code or "",
        branch_code=iban_obj.bban.branch_code or "",
        account_number=iban_obj.account_code or "",
        bban=str(iban_obj.bban),
        in_sepa_zone=iban_obj.in_sepa_zone,
    )


# Module-level WSDL path and cached client to avoid blocking WSDL parsing on every request
_VIES_WSDL_PATH = os.path.join(os.path.dirname(__file__), "wsdl", "checkVatService.wsdl")
_vat_transport = AsyncTransport(timeout=30)
_vat_client = zeep.AsyncClient(wsdl=_VIES_WSDL_PATH, transport=_vat_transport)


@contextlib.asynccontextmanager
async def _vat_check_context(vat_number: str):
    """Run VAT check with proper context management to avoid OpenTelemetry issues."""
    try:
        result = await _vat_client.service.checkVat(
            countryCode=vat_number[:2], vatNumber=vat_number[2:]
        )
        response = zeep.helpers.serialize_object(result)
        yield response
    finally:
        pass


@api.get("/vat", summary="Validate VAT number")
@rate_limit(RATE_LIMIT)
async def validate_vat(
    request: Request,
    vat_number: Annotated[str, Query(description="VAT number to validate")],
) -> ValidateVATResponseSchema:
    """Validates an EU VAT number using the VIES service."""
    # Validate VAT number format
    if not re.match(VAT_PATTERN, vat_number):
        raise BadRequest(
            detail="Invalid VAT number format. Expected format: Two-letter country code followed by 8-12 digits or letters."
        )

    # Brexit check
    if vat_number.startswith("GB"):
        raise BadRequest(
            detail="As of 01/01/2021, the VoW service to validate UK (GB) VAT numbers ceased to exist "
            "while a new service to validate VAT numbers of businesses operating under the Protocol "
            'on Ireland and Northern Ireland appeared. These VAT numbers are starting with the "XI" prefix.'
        )

    try:
        # Use context manager to properly handle OpenTelemetry context
        async with _vat_check_context(vat_number) as response:
            return ValidateVATResponseSchema(
                valid=response["valid"],
                vat_number=response["vatNumber"],
                name=response["name"],
                address=(response["address"].strip() if response["address"] else ""),
                country_code=response["countryCode"],
            )
    except zeep.exceptions.Fault as e:
        raise BadRequest(detail=e.message)


@api.get("/rates", summary="Get exchange rates")
@rate_limit(RATE_LIMIT)
async def rates(
    request: Request,
    base: Annotated[str, Query(description="Base currency for rates")] = "EUR",
    symbols: Annotated[
        Optional[str], Query(description="Comma-separated currency symbols to filter")
    ] = None,
    date: Annotated[
        Optional[str],
        Query(description="Date for historical rates (YYYY-MM-DD)"),
    ] = None,
) -> RatesResponseSchema:
    """Returns exchange rates from the European Central Bank."""
    # Validate base currency
    if base not in CURRENCY_SYMBOLS:
        raise BadRequest(detail=f"Base currency '{base}' is not supported.")

    # Parse and validate symbols
    symbols_list = None
    if symbols:
        symbols_list = symbols.split(",")
        for symbol in symbols_list:
            if symbol not in CURRENCY_SYMBOLS:
                raise BadRequest(detail=f"Currency '{symbol}' is not supported.")

    # Parse and validate date
    query_date = pendulum.now().date()
    if date:
        try:
            query_date = pendulum.parse(date, strict=True).date()
        except (ValueError, pendulum.parsing.exceptions.ParserError):
            raise BadRequest(detail=f"Invalid date format: '{date}'. Expected format: YYYY-MM-DD")

    # Get the rates data
    record = await Rate.objects.filter(date__lte=query_date).order_by("-date").afirst()
    if not record:
        raise NotFound(detail="No rate data available for the specified date.")

    # Base re-calculation - only include currencies defined in CURRENCY_SYMBOLS
    rates_data = {"EUR": 1.0}
    rates_data.update({k: float(v) for k, v in record.rates.items() if k in CURRENCY_SYMBOLS})

    if base != "EUR":
        if base not in rates_data:
            raise BadRequest(detail=f"Base currency '{base}' not available in current rates data")
        base_rate = Decimal(str(rates_data[base]))
        rates_data = {
            currency: float(Decimal(str(rate)) / base_rate) for currency, rate in rates_data.items()
        }
        rates_data["EUR"] = float(Decimal("1") / base_rate)

    # Filter symbols
    if symbols_list:
        rates_data = {k: v for k, v in rates_data.items() if k in symbols_list}

    return RatesResponseSchema(
        date=record.date.isoformat(),
        base=base,
        rates=rates_data,
    )


@api.get("/", summary="API Information")
@rate_limit(RATE_LIMIT)
async def root(request: Request) -> RootResponseSchema:
    """Returns general information about the API, its status, and available endpoints."""
    # Static endpoint list for Django Bolt (simpler than introspection)
    endpoints = {
        "countries": urljoin(settings.BASE_URL, "/countries"),
        "currencies": urljoin(settings.BASE_URL, "/currencies"),
        "geolocate": urljoin(settings.BASE_URL, "/geolocate"),
        "iban": urljoin(settings.BASE_URL, "/iban"),
        "vat": urljoin(settings.BASE_URL, "/vat"),
        "rates": urljoin(settings.BASE_URL, "/rates"),
    }

    return RootResponseSchema(
        name="VATComply API",
        version="1.0.0",
        status="operational",
        description="VAT validation API, geolocation tools, and ECB exchange rates",
        documentation=urljoin(settings.BASE_URL, "docs"),
        endpoints=endpoints,
        contact="support@vatcomply.com",
    )
