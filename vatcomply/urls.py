from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from vatcomply.views import (
    CountriesView,
    CurrenciesView,
    GeolocateView,
    RatesView,
    VATView,
)

# Admin header
admin.site.site_header = "VATcomply"

urlpatterns = [
    path("admin/", admin.site.urls),
    # API
    path("countries", CountriesView.as_view()),
    path("currencies", CurrenciesView.as_view()),
    path("geolocate", GeolocateView.as_view()),
    path("vat", VATView.as_view()),
    path("rates", RatesView.as_view()),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
