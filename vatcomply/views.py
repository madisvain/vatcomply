from decimal import Decimal

import pendulum
import zeep
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from vatcomply.http import UJsonResponse as JsonResponse
from vatcomply.models import Country, Rate
from vatcomply.serializers import RatesQueryValidationModel, VATValidationModel


@method_decorator(csrf_exempt, name="dispatch")
class CountriesView(View):
    async def get(self, request):
        countries = []
        async for country in Country.objects.order_by("iso2").all():
            countries.append(
                {
                    "iso2": country.iso2,
                    "iso3": country.iso3,
                    "name": country.name,
                    "numeric_code": country.numeric_code,
                    "phone_code": country.phone_code,
                    "capital": country.capital,
                    "currency": country.currency,
                    "tld": country.tld,
                    "region": country.region,
                    "subregion": country.subregion,
                    "latitude": Decimal(country.latitude),
                    "longitude": Decimal(country.longitude),
                    "emoji": country.emoji,
                }
            )

        return JsonResponse(countries)


@method_decorator(csrf_exempt, name="dispatch")
class GeolocateView(View):
    async def get(self, request):
        country_code = request.headers.get("CF-IPCountry")
        ip = request.headers.get("CF-Connecting-IP")

        country_code = "EE"
        if not country_code:
            return JsonResponse(
                {
                    "error": "Country code not received from CloudFlare headers `CF-IPCountry`."
                },
                status=404,
            )

        # Get the country data
        try:
            record = await Country.objects.aget(iso2=country_code.upper())
        except Country.DoesNotExist:
            return JsonResponse(
                {"error": f"Data for country code `{country_code.upper()}` not found."},
                status=404,
            )

        return JsonResponse(
            {
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
            },
        )


@method_decorator(csrf_exempt, name="dispatch")
class VATView(View):
    async def get(self, request):
        try:
            query = VATValidationModel(**request.GET.dict())
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
                    "address": response["address"].strip()
                    if response["address"]
                    else "",
                    "country_code": response["countryCode"],
                }
            )
        except ValidationError as e:
            return JsonResponse(e, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class RatesView(View):
    async def get(self, request):
        query_params = request.GET.dict()
        if "date" in request.GET:
            query_params["date"] = request.GET["date"]

        try:
            query = RatesQueryValidationModel(**query_params)

            # Find the date
            date = query.date if query.date else pendulum.now().date()

            # Get the rates data
            record = (
                await Rate.objects.filter(date__lte=date).order_by("-date").afirst()
            )

            # Base re-calculation
            rates = {"EUR": 1}
            rates.update(record.rates)
            if query.base and query.base != "EUR":
                base_rate = Decimal(record.rates[query.base])
                rates = {
                    currency: Decimal(rate) / base_rate
                    for currency, rate in rates.items()
                }
                rates.update({"EUR": Decimal(1) / base_rate})

            # Symbols
            if query.symbols:
                for rate in list(rates):
                    if rate not in query.symbols:
                        del rates[rate]

            return JsonResponse(
                {"date": record.date.isoformat(), "base": query.base, "rates": rates}
            )
        except ValidationError as e:
            return JsonResponse(e, status=400)
