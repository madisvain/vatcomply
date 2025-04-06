from django.contrib import admin
from django.urls import path

from vatcomply.api import api

# Admin header
admin.site.site_header = "VATcomply"

urlpatterns = [
    path("admin/", admin.site.urls),
    # API
    path("", api.urls),
]
