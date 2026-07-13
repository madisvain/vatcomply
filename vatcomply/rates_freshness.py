"""Helpers for detecting and reporting stale ECB exchange-rate data."""

from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings

from vatcomply.models import Rate


def is_rates_stale(latest: date | None, *, today: date | None = None) -> bool:
    """Return True when there is no rate data or it is older than the max age.

    Args:
        latest: Most recent Rate.date in the database, or None if empty.
        today: Reference date (defaults to date.today()). Injectable for tests.
    """
    if latest is None:
        return True
    ref = today if today is not None else date.today()
    max_age = settings.RATES_MAX_AGE_DAYS
    return (ref - latest).days > max_age


async def latest_rate_date() -> date | None:
    """Return the most recent Rate.date, or None if the table is empty."""
    return await Rate.objects.order_by("-date").values_list("date", flat=True).afirst()


async def check_rates_freshness() -> tuple[bool, str]:
    """django-bolt health check: rates data is present and recent enough."""
    latest = await latest_rate_date()
    max_age = settings.RATES_MAX_AGE_DAYS

    if latest is None:
        return False, "No exchange rate data in database"

    if is_rates_stale(latest):
        age_days = (date.today() - latest).days
        return (
            False,
            f"Exchange rates stale: latest={latest.isoformat()} "
            f"({age_days} days old, max={max_age})",
        )

    return True, f"Exchange rates OK (latest={latest.isoformat()})"


def rates_age_days(latest: date, *, today: date | None = None) -> int:
    """Calendar days between latest rate date and today (or ref date)."""
    ref = today if today is not None else date.today()
    return (ref - latest).days


def max_acceptable_rate_date(*, today: date | None = None) -> date:
    """Oldest Rate.date that is still considered fresh."""
    ref = today if today is not None else date.today()
    return ref - timedelta(days=settings.RATES_MAX_AGE_DAYS)
