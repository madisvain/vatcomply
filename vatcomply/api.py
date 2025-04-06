import dpath
import pendulum
import zeep

from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse, HttpRequest
from ninja import NinjaAPI, Query
from ninja.errors import ValidationError
from pydantic import ValidationError as PydanticValidationError

from vatcomply.constants import CurrencySymbol
from vatcomply.models import Country, Rate
from vatcomply.schemas import (
    CountrySchema,
    CurrencySchema,
    GeolocateResponse,
    ErrorResponse,
    VATQueryParamsSchema,
    RatesResponseSchema,
    RatesQueryParamsSchema,
)

api = NinjaAPI()


# Exception handlers
@api.exception_handler(ValidationError)
@api.exception_handler(PydanticValidationError)
def validation_errors(request, exc):
    """
    Simplifies Pydantic validation errors to field: [messages] format
    where messages is always a list of error messages
    """
    errors = {}

    if isinstance(exc, PydanticValidationError):
        exc.errors = exc.errors()

    for error in exc.errors:
        fields = tuple(filter(lambda x: x not in ["body", "payload"], error["loc"]))
        message = error["msg"]

        # Convert path to dpath format
        path = "/".join(str(x) for x in fields)

        if not path:
            if "non_field_errors" not in errors:
                errors["non_field_errors"] = []
            errors["non_field_errors"].append(message)
            continue

        # Check if the path already exists
        try:
            current_value = dpath.get(errors, path)
            # If the path exists, ensure it's a list and append the new message
            if not isinstance(current_value, list):
                dpath.set(errors, path, [current_value])
            dpath.get(errors, path).append(message)
        except KeyError:
            # If the path doesn't exist, create it with a list containing the message
            dpath.new(errors, path, [message])

    return JsonResponse(errors, status=422)


@api.get("/countries", response=list[CountrySchema], summary="Get list of countries")
async def countries(request):
    """
    Fetches a list of countries with their details.
    """
    countries = []
    async for country in Country.objects.order_by("iso2").all():
        countries.append(
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
                latitude=Decimal(country.latitude),
                longitude=Decimal(country.longitude),
                emoji=country.emoji,
            )
        )
    return countries


@api.get(
    "/currencies",
    response=dict[str, CurrencySchema],
    summary="Get list of supported currencies",
)
def get_currencies(request):
    currencies = {}
    for choice in CurrencySymbol.choices:
        symbol = choice[0]
        currencies[symbol] = CurrencySchema(
            name=choice[1],
            symbol=symbol,
        )
    return currencies


@api.get(
    "/geolocate",
    response={200: GeolocateResponse, 404: ErrorResponse},
    summary="Geolocate by IP",
)
async def geolocate(request: HttpRequest):
    country_code = request.headers.get("CF-IPCountry")
    ip = request.headers.get("CF-Connecting-IP")

    if not country_code:
        return 404, {
            "error": "Country code not received from CloudFlare headers `CF-IPCountry`."
        }

    try:
        record = await Country.objects.aget(iso2=country_code.upper())
    except Country.DoesNotExist:
        return 404, {
            "error": f"Data for country code `{country_code.upper()}` not found."
        }

    return 200, {
        "iso2": record.iso2,
        "iso3": record.iso3,
        "country_code": country_code.upper(),
        "name": record.name,
        "numeric_code": record.numeric_code,
        "phone_code": record.phone_code,
        "capital": record.capital,
        "currency": record.currency,
        "tld": record.tld,
        "region": record.region,
        "subregion": record.subregion,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "emoji": record.emoji,
        "ip": ip,
    }


@api.get("/vat")
async def validate_vat(request, query: Query[VATQueryParamsSchema]):
    client = zeep.AsyncClient(wsdl=str(settings.VIES_WSDL))
    try:
        response = await zeep.helpers.serialize_object(
            client.service.checkVat(
                countryCode=query.vat_number[:2], vatNumber=query.vat_number[2:]
            )
        )
    except zeep.exceptions.Fault as e:
        return JsonResponse({"error": e.message}, status=400)

    return JsonResponse(
        {
            "valid": response["valid"],
            "vat_number": response["vatNumber"],
            "name": response["name"],
            "address": (response["address"].strip() if response["address"] else ""),
            "country_code": response["countryCode"],
        }
    )


@api.get("/rates", response=RatesResponseSchema)
async def rates(request, query: Query[RatesQueryParamsSchema]):
    # Find the date
    date = query.date if query.date else pendulum.now().date()

    # Get the rates data
    record = await Rate.objects.filter(date__lte=date).order_by("-date").afirst()

    # Base re-calculation
    rates = {"EUR": 1}
    rates.update(record.rates)
    if query.base and query.base != "EUR":
        base_rate = Decimal(record.rates[query.base])
        rates = {
            currency: Decimal(rate) / base_rate for currency, rate in rates.items()
        }
        rates.update({"EUR": Decimal(1) / base_rate})

    # Symbols
    if query.symbols:
        for rate in list(rates):
            if rate not in query.symbols:
                del rates[rate]

    return RatesResponseSchema(
        date=record.date.isoformat(), base=query.base, rates=rates
    )
