"""
VATcomply API

Provides VAT validation, currency rates, geolocation, and IBAN validation endpoints.
"""

import logging
import os
import re
from decimal import Decimal
from typing import Annotated

import pendulum
import zeep
import zeep.helpers
from django.conf import settings
from django_bolt import BoltAPI, Request
from django_bolt.exceptions import BadRequest, NotFound
from django_bolt.health import register_health_checks
from django_bolt.middleware import rate_limit
from django_bolt.openapi import OpenAPIConfig
from django_bolt.params import Query
from pycountry import countries as pycountries
from schwifty import IBAN
from urllib.parse import urljoin
from zeep.transports import AsyncTransport

logger = logging.getLogger(__name__)

from django.db import models

from vatcomply.constants import CurrencySymbol
from vatcomply.currency_metadata import get_currency_metadata
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
CURRENCY_SYMBOLS = {choice[0] for choice in CurrencySymbol.choices}

# Configure rate limiting based on settings
if settings.THROTTLE:
    throttle = rate_limit(rps=2, burst=4)
else:
    def throttle(f):
        return f

# Create the API instance
api = BoltAPI(
    middleware=[CustomErrorMiddleware],
    openapi_config=OpenAPIConfig(
        title="Vatcomply API",
        version="1.0.0",
        description="API for automated VAT compliance and currency conversion.",
    ),
)

# Register health check endpoints (/health, /ready)
register_health_checks(api)


@api.get("/countries", summary="Get list of countries")
@throttle
async def countries(
    request: Request,
    search: Annotated[str | None, Query(description="Search by country name, ISO2, or ISO3 code")] = None,
    region: Annotated[str | None, Query(description="Filter by region (e.g. Europe)")] = None,
    subregion: Annotated[str | None, Query(description="Filter by subregion (e.g. Northern Europe)")] = None,
    currency: Annotated[str | None, Query(description="Filter by currency code (e.g. EUR)")] = None,
) -> list[CountrySchema]:
    """Fetches a list of countries with their details."""
    qs = Country.objects.order_by("iso2")
    if search:
        qs = qs.filter(
            models.Q(name__icontains=search)
            | models.Q(iso2__icontains=search)
            | models.Q(iso3__icontains=search)
        )
    if region:
        qs = qs.filter(region__iexact=region)
    if subregion:
        qs = qs.filter(subregion__iexact=subregion)
    if currency:
        qs = qs.filter(currency__iexact=currency)
    result = []
    async for country in qs:
        result.append(CountrySchema.from_model(country))
    return result


@api.get("/currencies", summary="Get list of supported currencies")
@throttle
def get_currencies(
    request: Request,
    search: Annotated[str | None, Query(description="Search by currency code or name")] = None,
) -> dict[str, CurrencySchema]:
    """Returns all supported currencies, optionally filtered by a search term."""
    currencies = {}
    for choice in CurrencySymbol.choices:
        symbol = choice[0]
        name = choice[1]
        if search:
            term = search.lower()
            if term not in symbol.lower() and term not in name.lower():
                continue
        meta = get_currency_metadata(symbol)
        currencies[symbol] = CurrencySchema(
            name=name,
            symbol=symbol,
            **meta,
        )
    return currencies


@api.get("/geolocate", summary="Geolocate by IP")
@throttle
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
@throttle
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


# Lazy-initialized WSDL client to avoid crash at import if WSDL file is missing
_VIES_WSDL_PATH = os.path.join(os.path.dirname(__file__), "wsdl", "checkVatService.wsdl")
_vat_client = None


def _get_vat_client():
    """Lazy-init the zeep AsyncClient on first use."""
    global _vat_client
    if _vat_client is None:
        transport = AsyncTransport(timeout=10)
        _vat_client = zeep.AsyncClient(wsdl=_VIES_WSDL_PATH, transport=transport)
    return _vat_client


async def _vat_check(vat_number: str):
    """Run VAT check and return serialized response."""
    client = _get_vat_client()
    result = await client.service.checkVat(
        countryCode=vat_number[:2], vatNumber=vat_number[2:]
    )
    return zeep.helpers.serialize_object(result)


@api.get("/vat", summary="Validate VAT number")
@throttle
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
        response = await _vat_check(vat_number)
        return ValidateVATResponseSchema(
            valid=response["valid"],
            vat_number=response["vatNumber"],
            name=response["name"],
            address=(response["address"].strip() if response["address"] else ""),
            country_code=response["countryCode"],
        )
    except zeep.exceptions.Fault as e:
        logger.error("VIES SOAP fault for VAT %s: %s", vat_number, e.message)
        raise BadRequest(detail=e.message)


@api.get("/rates", summary="Get exchange rates")
@throttle
async def rates(
    request: Request,
    base: Annotated[str, Query(description="Base currency for rates")] = "EUR",
    symbols: Annotated[
        str | None, Query(description="Comma-separated currency symbols to filter")
    ] = None,
    date: Annotated[
        str | None,
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

    # Parse and validate date (enforce YYYY-MM-DD format)
    query_date = pendulum.now().date()
    if date:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            raise BadRequest(detail=f"Invalid date format: '{date}'. Expected format: YYYY-MM-DD")
        try:
            query_date = pendulum.parse(date, strict=True).date()
        except (ValueError, pendulum.parsing.exceptions.ParserError):
            raise BadRequest(detail=f"Invalid date: '{date}'. Expected a valid date in YYYY-MM-DD format.")

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
            currency: float(round(Decimal(str(rate)) / base_rate, 6)) for currency, rate in rates_data.items()
        }
        rates_data["EUR"] = float(round(Decimal("1") / base_rate, 6))

    # Filter symbols
    if symbols_list:
        rates_data = {k: v for k, v in rates_data.items() if k in symbols_list}

    return RatesResponseSchema(
        date=record.date.isoformat(),
        base=base,
        rates=rates_data,
    )


@api.get("/", summary="API Information")
@throttle
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
