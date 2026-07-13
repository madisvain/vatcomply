from datetime import date, timedelta

from django.test import override_settings

from vatcomply.rates_freshness import is_rates_stale, max_acceptable_rate_date, rates_age_days


@override_settings(RATES_MAX_AGE_DAYS=4)
def test_is_rates_stale_no_rows():
    assert is_rates_stale(None, today=date(2026, 7, 14)) is True


@override_settings(RATES_MAX_AGE_DAYS=4)
def test_is_rates_stale_fresh():
    today = date(2026, 7, 14)
    assert is_rates_stale(date(2026, 7, 13), today=today) is False
    assert is_rates_stale(date(2026, 7, 14), today=today) is False
    # Exactly max age days old is still fresh (not > max)
    assert is_rates_stale(date(2026, 7, 10), today=today) is False


@override_settings(RATES_MAX_AGE_DAYS=4)
def test_is_rates_stale_too_old():
    today = date(2026, 7, 14)
    assert is_rates_stale(date(2026, 7, 9), today=today) is True
    assert is_rates_stale(date(2026, 6, 25), today=today) is True


@override_settings(RATES_MAX_AGE_DAYS=4)
def test_rates_age_days_and_max_acceptable():
    today = date(2026, 7, 14)
    assert rates_age_days(date(2026, 7, 10), today=today) == 4
    assert max_acceptable_rate_date(today=today) == today - timedelta(days=4)
