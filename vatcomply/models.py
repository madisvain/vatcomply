import uuid

from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class Rate(models.Model):
    date = models.DateField(
        unique=True, primary_key=True, editable=False, db_index=True
    )
    rates = models.JSONField(default=dict)

    class Meta:
        ordering = ["-date"]


class Country(models.Model):
    iso2 = models.CharField(max_length=2, unique=True, primary_key=True)
    iso3 = models.CharField(max_length=3)
    name = models.CharField(max_length=200)
    numeric_code = models.IntegerField()
    phone_code = models.CharField(max_length=3)
    capital = models.CharField(max_length=200)
    currency = models.CharField(max_length=200)
    tld = models.CharField(max_length=200)
    region = models.CharField(max_length=200)
    subregion = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    emoji = models.CharField(max_length=1)

    class Meta:
        ordering = ["name"]
