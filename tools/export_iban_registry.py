#!/usr/bin/env python3
"""Export schwifty 2026.3.0 IBAN specs, bank names, and country names.

The Rust service vendors this file so bank names and error text match
production (schwifty) without a Python runtime. Run with the venv that
has schwifty==2026.3.0 installed:

    /tmp/vatcomply-py/bin/python tools/export_iban_registry.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import schwifty.bban  # noqa: F401  (builds indexes)
import schwifty.bic  # noqa: F401
import schwifty.iban  # noqa: F401
from pycountry import countries
from schwifty import registry
from schwifty.bic import BIC
from schwifty.exceptions import SchwiftyException

OUT = Path(__file__).resolve().parents[1] / "data" / "iban_registry.json"


def main() -> None:
    specs = registry.get("iban")
    assert isinstance(specs, dict)
    banks = registry.get("bank_code")
    assert isinstance(banks, dict)

    countries_out: dict[str, dict] = {}
    for code in sorted(specs):
        spec = specs[code]
        country = countries.get(alpha_2=code)
        positions = spec.get("positions") or {}
        lookup = spec.get("bic_lookup_components") or ["bank_code"]
        countries_out[code] = {
            "name": country.name if country else "",
            "in_sepa_zone": bool(spec.get("in_sepa_zone")),
            "iban_length": int(spec["iban_length"]),
            "bban_length": int(spec["bban_length"]),
            "bban_spec": spec["bban_spec"],
            "positions": {key: list(value) for key, value in positions.items()},
            "bic_lookup": list(lookup),
        }

    banks_out: dict[str, dict[str, list[str]]] = {}
    for (country_code, bank_code), entries in banks.items():
        if not country_code or not bank_code or not entries:
            continue
        name = entries[0].get("name") or ""
        try:
            bic = str(BIC.from_bank_code(country_code, bank_code))
        except SchwiftyException:
            bic = ""
        banks_out.setdefault(country_code, {})[bank_code] = [name, bic]

    payload = {
        "schwifty": "2026.3.0",
        "countries": countries_out,
        "banks": banks_out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(text)} bytes, {len(countries_out)} countries, {sum(len(v) for v in banks_out.values())} banks)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
