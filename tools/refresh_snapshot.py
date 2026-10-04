#!/usr/bin/env python3
"""Build the versioned ECB rates snapshot embedded in the v2 binary.

Snapshot bytes (before gzip):

    VATSNAP1\\n
    <sha256 hex of the JSON body>\\n
    <JSON body>

JSON is version 1. ``dates`` is an ascending list of [iso_date, [[code, decimal], ...]]
in ECB XML order. Decimal strings are kept verbatim. EUR is not stored.

Also writes tests/fixtures/pyfloat_oracle.json: every distinct ECB decimal mapped
to CPython's json token, plus cross-rate samples using the v1 formula.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import random
import sys
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path("/tmp/vatcomply-ecb")
HIST_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
HIST_90_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
NS = {"e": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}

ALLOW = [
    "EUR", "USD", "JPY", "BGN", "CZK", "DKK", "GBP", "HUF", "PLN", "RON", "SEK", "CHF",
    "ISK", "NOK", "HRK", "RUB", "TRY", "AUD", "BRL", "CAD", "CNY", "HKD", "IDR", "ILS",
    "INR", "KRW", "MXN", "MYR", "NZD", "PHP", "SGD", "THB", "ZAR",
]
ALLOW_SET = set(ALLOW)


def download(url: str, dest: Path) -> bytes:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "vatcomply-snapshot/2"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return data


def parse_hist(xml: bytes) -> list[tuple[str, list[tuple[str, str]]]]:
    envelope = ElementTree.fromstring(xml)
    cubes = envelope.findall("./e:Cube/e:Cube[@time]", NS)
    days: list[tuple[str, list[tuple[str, str]]]] = []
    for cube in cubes:
        pairs: list[tuple[str, str]] = []
        for child in list(cube):
            code = child.attrib.get("currency")
            rate = child.attrib.get("rate")
            if code and rate:
                pairs.append((code, rate))
        days.append((cube.attrib["time"], pairs))
    days.sort(key=lambda item: item[0])
    return days


def snapshot_json(days: list[tuple[str, list[tuple[str, str]]]]) -> bytes:
    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dates": days,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def encode_snapshot(body: bytes) -> bytes:
    digest = hashlib.sha256(body).hexdigest()
    raw = b"VATSNAP1\n" + digest.encode("ascii") + b"\n" + body
    return gzip.compress(raw, mtime=0)


def json_token(value: float) -> str:
    return json.dumps(value, separators=(",", ":"))


def cross_token(rate_string: str, base_string: str) -> str:
    """v1 formula. rate_string '1' means Decimal('1') (the injected euro)."""
    base_rate = Decimal(str(float(base_string)))
    if rate_string == "1":
        numer = Decimal("1")
    else:
        numer = Decimal(str(float(rate_string)))
    return json_token(float(round(numer / base_rate, 6)))


def build_oracle(days: list[tuple[str, list[tuple[str, str]]]]) -> dict:
    tokens: dict[str, str] = {}
    for _date, pairs in days:
        for _code, decimal in pairs:
            if decimal not in tokens:
                tokens[decimal] = json_token(float(decimal))
    # Stable cross samples: every golden base below, plus a fixed sample of pairs.
    interesting_bases = ["1.1574", "1.9558", "7.5365", "1.0666", "1.175", "1.1225", "137"]
    cross = []
    seen = set()

    def add(rate: str, base: str) -> None:
        key = (rate, base)
        if key in seen or rate == base:
            return
        seen.add(key)
        cross.append({"rate": rate, "base": base, "token": cross_token(rate, base)})

    for base in interesting_bases:
        if base in tokens or base == "1":
            add("1", base)
    # A few explicit pairs called out in PLAN.md, using the ECB strings.
    explicit = [
        ("1", "1.1574"),
        ("0.8764", "1.1574"),
        ("1", "7.5365"),
        ("1.0666", "7.5365"),
        ("1", "1.9558"),
        ("1.175", "1.9558"),
    ]
    for rate, base in explicit:
        add(rate, base)

    rng = random.Random(20261004)
    pool = sorted(tokens)
    for _ in range(400):
        rate = rng.choice(pool)
        base = rng.choice(pool)
        add(rate, base)
    for base in interesting_bases:
        if base not in tokens:
            continue
        for rate in rng.sample(pool, k=min(40, len(pool))):
            add(rate, base)

    return {"tokens": tokens, "cross": cross}


def render_eur(date: str, pairs: list[tuple[str, str]], symbols: str | None, base: str) -> tuple[int, str]:
    """Mirror vatcomply/api.py for one already-selected row."""
    if base not in ALLOW_SET:
        return 400, json.dumps({"detail": f"Base currency '{base}' is not supported."}, separators=(",", ":"))
    symbols_list = None
    if symbols:
        symbols_list = symbols.split(",")
        for symbol in symbols_list:
            if symbol not in ALLOW_SET:
                return 400, json.dumps(
                    {"detail": f"Currency '{symbol}' is not supported."}, separators=(",", ":")
                )
    rates: dict[str, float] = {"EUR": 1.0}
    for code, decimal in pairs:
        if code in ALLOW_SET:
            rates[code] = float(decimal)
    if base != "EUR":
        if base not in rates:
            return 400, json.dumps(
                {"detail": f"Base currency '{base}' not available in current rates data"},
                separators=(",", ":"),
            )
        base_rate = Decimal(str(rates[base]))
        rates = {
            currency: float(round(Decimal(str(rate)) / base_rate, 6))
            for currency, rate in rates.items()
        }
        rates["EUR"] = float(round(Decimal("1") / base_rate, 6))
    if symbols_list is not None:
        rates = {key: value for key, value in rates.items() if key in symbols_list}
    body = json.dumps({"date": date, "base": base, "rates": rates}, ensure_ascii=False, separators=(",", ":"))
    return 200, body


def lookup(days: list[tuple[str, list[tuple[str, str]]]], query: str):
    best = None
    for date, pairs in days:
        if date <= query:
            best = (date, pairs)
        else:
            break
    return best


def main() -> None:
    hist = download(HIST_URL, CACHE / "eurofxref-hist.xml")
    download(HIST_90_URL, CACHE / "eurofxref-hist-90d.xml")
    days = parse_hist(hist)
    body = snapshot_json(days)
    blob = encode_snapshot(body)
    out = ROOT / "data" / "rates-snapshot.json.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    oracle = build_oracle(days)
    oracle_path = ROOT / "tests" / "fixtures" / "pyfloat_oracle.json"
    oracle_path.parent.mkdir(parents=True, exist_ok=True)
    oracle_path.write_text(
        json.dumps(oracle, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    print(
        f"days={len(days)} first={days[0][0]} last={days[-1][0]} "
        f"snapshot={out.stat().st_size} oracle_tokens={len(oracle['tokens'])} "
        f"cross={len(oracle['cross'])} oracle_bytes={oracle_path.stat().st_size}"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
