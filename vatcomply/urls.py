# from django.contrib import admin
from django.urls import path

from vatcomply.views import CountriesView, GeolocateView, RatesView, VATView


urlpatterns = [
    # path("admin/", admin.site.urls),
    # API
    path("countries", CountriesView.as_view()),
    path("geolocate", GeolocateView.as_view()),
    path("vat", VATView.as_view()),
    path("rates", RatesView.as_view()),
]
