"""
Currency metadata enrichment using pycountry and babel.

Builds lookup tables at import time and provides get_currency_metadata()
for enriching currency responses with additional fields.
"""

from datetime import date

import pycountry
from babel.core import get_global
from babel.numbers import get_currency_precision, get_currency_symbol


def _build_currency_to_territories():
    """Build reverse mapping from currency code to list of territory codes.

    Iterates babel's territory_currencies and returns two dicts:
    - all_territories: all currently-active territories for each currency
    - tender_territories: only tender=True territories
    """
    today = date.today()
    territory_currencies = get_global("territory_currencies")

    all_territories: dict[str, list[str]] = {}
    tender_territories: dict[str, list[str]] = {}
    # Track if a currency ever appeared in any territory (for historical detection)
    ever_used: set[str] = set()

    for territory, currencies in territory_currencies.items():
        for currency_code, start, end, tender in currencies:
            ever_used.add(currency_code)
            # Check if currently active
            if start:
                start_date = date(*start)
                if start_date > today:
                    continue
            if end:
                end_date = date(*end)
                if end_date < today:
                    continue
            all_territories.setdefault(currency_code, []).append(territory)
            if tender:
                tender_territories.setdefault(currency_code, []).append(territory)

    return all_territories, tender_territories, ever_used


# Build cached lookup tables at import time
_all_territories, _tender_territories, _ever_used = _build_currency_to_territories()

# Cache currency_fractions from babel
_currency_fractions = get_global("currency_fractions")


def get_currency_metadata(code: str) -> dict:
    """Return enriched metadata dict for a given currency code."""
    # numeric_code from pycountry
    pc = pycountry.currencies.get(alpha_3=code)
    numeric_code = pc.numeric if pc else ""

    # currency_symbol from babel
    currency_symbol = get_currency_symbol(code, locale="en")

    # decimal_places from babel
    decimal_places = get_currency_precision(code)

    # rounding from babel currency_fractions
    default_fractions = _currency_fractions.get("DEFAULT", (2, 0, 2, 0))
    fractions = _currency_fractions.get(code, default_fractions)
    rounding = fractions[1]

    # countries and official_countries from cached reverse mapping
    countries = sorted(_all_territories.get(code, []))
    official_countries = sorted(_tender_territories.get(code, []))

    # historical: currency was used by some territory but no longer active anywhere
    historical = code in _ever_used and len(countries) == 0

    return {
        "numeric_code": numeric_code,
        "currency_symbol": currency_symbol,
        "currency_symbol_narrow": None,
        "decimal_places": decimal_places,
        "rounding": rounding,
        "countries": countries,
        "official_countries": official_countries,
        "historical": historical,
    }
