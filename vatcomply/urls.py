from django.contrib import admin
from django.urls import path

# Admin header
admin.site.site_header = "VATcomply"

# Django Bolt serves API routes via `python manage.py runbolt`
# This urlpatterns only handles Django admin
urlpatterns = [
    path("admin/", admin.site.urls),
]
