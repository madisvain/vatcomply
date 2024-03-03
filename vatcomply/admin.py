from django.contrib import admin
from django.contrib.admin import site

from vatcomply.models import Rate, Country


@admin.register(Rate, site=site)
class RateAdmin(admin.ModelAdmin):
    list_display = [
        "date",
    ]


@admin.register(Country, site=site)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["iso2", "name", "currency", "region", "emoji"]
