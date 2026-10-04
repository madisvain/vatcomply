#!/usr/bin/env python3
"""Record production responses from https://api.vatcomply.com.

Sends a browser User-Agent and sleeps 0.7s between calls so the capture
stays under the production 2 rps limit. Compares /rates bodies to the ECB
history plus the v1 float formula and exits non-zero on a mismatch.

No Rust test calls this script. Run it when refreshing fixtures.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_snapshot import (  # noqa: E402
    CACHE,
    download,
    lookup,
    parse_hist,
    render_eur,
)

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.vatcomply.com"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
SLEEP = 0.7

# (name, method, path, extra headers, body_file or None)
REQUESTS: list[tuple[str, str, str, dict[str, str], str | None]] = [
    ("root", "GET", "/", {}, None),
    ("countries", "GET", "/countries", {}, "tests/fixtures/countries_body.json"),
    ("currencies", "GET", "/currencies", {}, "data/currencies.json"),
    ("vat_rates", "GET", "/vat_rates", {}, "data/vat_rates.json"),
    ("countries_estonia", "GET", "/countries?search=Estonia", {}, None),
    ("countries_empty", "GET", "/countries?search=zzzzzzz", {}, None),
    ("currencies_usd", "GET", "/currencies?search=usd", {}, None),
    ("currencies_empty", "GET", "/currencies?search=zzzzzzz", {}, None),
    ("vat_rates_de", "GET", "/vat_rates?country_code=DE", {}, None),
    ("vat_rates_de_lower", "GET", "/vat_rates?country_code=de", {}, None),
    ("vat_rates_el", "GET", "/vat_rates?country_code=EL", {}, None),
    ("vat_rates_zz", "GET", "/vat_rates?country_code=ZZ", {}, None),
    ("vat_rates_gr", "GET", "/vat_rates?country_code=GR", {}, None),
    ("health", "GET", "/health", {}, None),
    ("ready", "GET", "/ready", {}, None),
    ("healthz_absent", "GET", "/healthz", {}, None),
    ("readyz_absent", "GET", "/readyz", {}, None),
    ("not_found", "GET", "/nope", {}, None),
    ("post_rates", "POST", "/rates", {}, None),
    ("head_rates", "HEAD", "/rates", {}, None),
    (
        "options_root",
        "OPTIONS",
        "/",
        {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
        None,
    ),
    ("get_with_origin", "GET", "/health", {"Origin": "https://example.com"}, None),
    ("rates_foo_ignored", "GET", "/rates?foo=1", {}, None),
    ("rates_latest", "GET", "/rates", {}, None),
    ("rates_trailing_slash", "GET", "/rates/", {}, None),
    ("rates_date_empty", "GET", "/rates?date=", {}, None),
    ("rates_symbols_empty", "GET", "/rates?symbols=", {}, None),
    ("rates_base_empty", "GET", "/rates?base=", {}, None),
    ("rates_base_lower", "GET", "/rates?base=usd", {}, None),
    ("rates_base_unknown", "GET", "/rates?base=XYZ", {}, None),
    ("rates_symbol_unknown", "GET", "/rates?symbols=NOPE", {}, None),
    ("rates_symbols_usd_jpy", "GET", "/rates?symbols=USD,JPY", {}, None),
    ("rates_symbols_gap", "GET", "/rates?symbols=USD,,GBP", {}, None),
    ("rates_symbols_space", "GET", "/rates?symbols=USD,%20JPY", {}, None),
    ("rates_date_abc", "GET", "/rates?date=abc", {}, None),
    ("rates_date_feb30", "GET", "/rates?date=2024-02-30", {}, None),
    ("rates_date_year", "GET", "/rates?date=2024", {}, None),
    ("rates_date_month", "GET", "/rates?date=2024-01", {}, None),
    ("rates_before_ecb", "GET", "/rates?date=1998-12-31", {}, None),
    ("rates_1999_01_04", "GET", "/rates?date=1999-01-04&symbols=USD,JPY", {}, None),
    ("rates_2018_10_13", "GET", "/rates?date=2018-10-13&symbols=USD,GBP,EUR", {}, None),
    ("rates_2018_10_12", "GET", "/rates?date=2018-10-12&symbols=USD,GBP,EUR", {}, None),
    ("rates_2018_usd_base", "GET", "/rates?date=2018-10-12&base=USD&symbols=EUR,GBP", {}, None),
    ("rates_2018_usd_gbp_only", "GET", "/rates?date=2018-10-12&base=USD&symbols=GBP", {}, None),
    ("rates_2018_01_01", "GET", "/rates?date=2018-01-01&symbols=USD", {}, None),
    ("rates_future", "GET", "/rates?date=2099-01-04&symbols=USD", {}, None),
    ("rates_2022_02_28", "GET", "/rates?date=2022-02-28&symbols=RUB,USD", {}, None),
    ("rates_2022_03_01", "GET", "/rates?date=2022-03-01&symbols=RUB,USD", {}, None),
    ("rates_rub_gone", "GET", "/rates?base=RUB&date=2022-03-02", {}, None),
    ("rates_hrk_base", "GET", "/rates?base=HRK&date=2022-12-30&symbols=EUR,USD", {}, None),
    ("rates_hrk_present", "GET", "/rates?date=2022-12-30&symbols=HRK,USD,EUR", {}, None),
    ("rates_hrk_gone", "GET", "/rates?base=HRK&date=2023-01-03", {}, None),
    ("rates_bgn_base", "GET", "/rates?base=BGN&date=2025-12-31&symbols=EUR,USD", {}, None),
    ("rates_bgn_present", "GET", "/rates?date=2025-12-31&symbols=BGN,USD,EUR", {}, None),
    ("rates_bgn_latest", "GET", "/rates?base=BGN", {}, None),
    ("rates_2017_12_29", "GET", "/rates?date=2017-12-29&symbols=USD", {}, None),
    ("rates_bgn_1999", "GET", "/rates?date=1999-01-04&base=BGN", {}, None),
    ("rates_duplicate_base", "GET", "/rates?base=USD&base=EUR&symbols=USD", {}, None),
    ("vat_missing", "GET", "/vat", {}, None),
    ("vat_empty", "GET", "/vat?vat_number=", {}, None),
    ("vat_short", "GET", "/vat?vat_number=123", {}, None),
    ("vat_lower", "GET", "/vat?vat_number=gb123456789", {}, None),
    ("vat_gb", "GET", "/vat?vat_number=GB123456789", {}, None),
    ("vat_invalid_input", "GET", "/vat?vat_number=XX12345678", {}, None),
    ("iban_missing", "GET", "/iban", {}, None),
    ("iban_empty", "GET", "/iban?iban=", {}, None),
    ("iban_digits", "GET", "/iban?iban=123", {}, None),
    ("iban_bad_checksum", "GET", "/iban?iban=DE89370400440532013001", {}, None),
    ("iban_de", "GET", "/iban?iban=DE89370400440532013000", {}, None),
    ("iban_gb", "GET", "/iban?iban=GB82WEST12345698765432", {}, None),
    ("iban_lower", "GET", "/iban?iban=de89370400440532013000", {}, None),
    ("iban_spaces", "GET", "/iban?iban=DE89%203704%200044%200532%200130%2000", {}, None),
    ("iban_unknown_country", "GET", "/iban?iban=XX89370400440532013000", {}, None),
    ("iban_short", "GET", "/iban?iban=DE8937040044053201300", {}, None),
    ("iban_no", "GET", "/iban?iban=NO9386011117947", {}, None),
    ("iban_fr", "GET", "/iban?iban=FR1420041010050500013M02606", {}, None),
]


def fetch(method: str, path: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    url = API + path
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, **headers})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw_headers = {key.lower(): value for key, value in resp.headers.items()}
            return resp.status, raw_headers, resp.read()
    except urllib.error.HTTPError as exc:
        raw_headers = {key.lower(): value for key, value in exc.headers.items()}
        return exc.code, raw_headers, exc.read()


def interesting_headers(headers: dict[str, str]) -> dict[str, str]:
    keep = {
        "content-type",
        "allow",
        "access-control-allow-origin",
        "access-control-allow-methods",
        "access-control-allow-headers",
        "retry-after",
        "x-ratelimit-limit",
    }
    return {key: headers[key] for key in sorted(keep) if key in headers}


def write_case(name: str, method: str, path: str, req_headers: dict, status: int, resp_headers: dict, body: bytes, body_file: str | None) -> None:
    golden_dir = ROOT / "tests" / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)
    if body_file:
        dest = ROOT / body_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
    text = body.decode("utf-8")
    case = {
        "name": name,
        "request": {"method": method, "path": path, "headers": req_headers},
        "status": status,
        "headers": interesting_headers(resp_headers),
        "body": None if body_file else text,
        "body_file": body_file,
    }
    (golden_dir / f"{name}.json").write_text(
        json.dumps(case, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{status} {method} {path} ({len(body)} bytes)")


def query_map(path: str) -> dict[str, str]:
    parsed = urllib.parse.urlsplit(path)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    # Last value wins, matching Django QueryDict.
    return dict(pairs)


def compare_rates(days) -> int:
    """Return the number of /rates goldens that disagree with ECB+pyfloat."""
    mismatches = 0
    golden_dir = ROOT / "tests" / "golden"
    for path in sorted(golden_dir.glob("rates_*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case["request"]["method"] != "GET":
            continue
        req_path = case["request"]["path"]
        route = urllib.parse.urlsplit(req_path).path.rstrip("/") or "/"
        if route != "/rates":
            continue
        params = query_map(req_path)
        base = params.get("base", "EUR")
        symbols = params.get("symbols")
        date = params.get("date")
        # Validation order matches vatcomply/api.py. Empty string is falsy.
        status, expected = None, None
        if base not in {
            "EUR", "USD", "JPY", "BGN", "CZK", "DKK", "GBP", "HUF", "PLN", "RON", "SEK", "CHF",
            "ISK", "NOK", "HRK", "RUB", "TRY", "AUD", "BRL", "CAD", "CNY", "HKD", "IDR", "ILS",
            "INR", "KRW", "MXN", "MYR", "NZD", "PHP", "SGD", "THB", "ZAR",
        }:
            status, expected = 400, json.dumps(
                {"detail": f"Base currency '{base}' is not supported."}, separators=(",", ":")
            )
        elif symbols:
            bad = next((part for part in symbols.split(",") if part not in {
                "EUR", "USD", "JPY", "BGN", "CZK", "DKK", "GBP", "HUF", "PLN", "RON", "SEK", "CHF",
                "ISK", "NOK", "HRK", "RUB", "TRY", "AUD", "BRL", "CAD", "CNY", "HKD", "IDR", "ILS",
                "INR", "KRW", "MXN", "MYR", "NZD", "PHP", "SGD", "THB", "ZAR",
            }), None)
            if bad is not None:
                status, expected = 400, json.dumps(
                    {"detail": f"Currency '{bad}' is not supported."}, separators=(",", ":")
                )
        if status is None and date:
            import re
            from datetime import datetime as dt

            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                status, expected = 400, json.dumps(
                    {"detail": f"Invalid date format: '{date}'. Expected format: YYYY-MM-DD"},
                    separators=(",", ":"),
                )
            else:
                try:
                    dt.strptime(date, "%Y-%m-%d")
                except ValueError:
                    status, expected = 400, json.dumps(
                        {"detail": f"Invalid date: '{date}'. Expected a valid date in YYYY-MM-DD format."},
                        separators=(",", ":"),
                    )
        if status is None:
            from datetime import datetime, timezone

            query = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            found = lookup(days, query)
            if found is None:
                status, expected = 404, json.dumps(
                    {"detail": "No rate data available for the specified date."},
                    separators=(",", ":"),
                )
            else:
                status, expected = render_eur(found[0], found[1], symbols, base)
        actual = case["body"]
        if case["status"] != status or actual != expected:
            mismatches += 1
            print(f"MISMATCH {path.name}")
            print(f"  status production={case['status']} computed={status}")
            print(f"  production={actual[:400]!r}")
            print(f"  computed  ={expected[:400]!r}")
    return mismatches


def write_excerpts(hist: bytes, hist90: bytes) -> None:
    from xml.etree import ElementTree

    ns = {"e": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}
    envelope = ElementTree.fromstring(hist)
    wanted = {
        "1999-01-04",
        "2017-12-29",
        "2018-10-12",
        "2022-02-28",
        "2022-03-01",
        "2022-03-02",
        "2022-12-30",
        "2023-01-02",
        "2023-01-03",
        "2025-12-31",
        "2026-01-02",
        "2026-10-02",
    }
    cubes = []
    for cube in envelope.findall("./e:Cube/e:Cube[@time]", ns):
        if cube.attrib.get("time") in wanted:
            cubes.append(ElementTree.tostring(cube, encoding="unicode"))
    excerpt = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" '
        'xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">\n'
        "<Cube>\n" + "\n".join(cubes) + "\n</Cube>\n</gesmes:Envelope>\n"
    )
    dest = ROOT / "tests" / "fixtures" / "ecb"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "excerpt.xml").write_text(excerpt, encoding="utf-8")
    (dest / "hist-90d.xml").write_bytes(hist90)
    print(f"ecb excerpt days={len(cubes)} 90d={len(hist90)}")


def write_vies_fixtures() -> None:
    dest = ROOT / "tests" / "fixtures" / "vies"
    dest.mkdir(parents=True, exist_ok=True)
    success = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <checkVatResponse xmlns="urn:ec.europa.eu:taxud:vies:services:checkVat:types">
      <countryCode>DE</countryCode>
      <vatNumber>100</vatNumber>
      <requestDate>2026-10-04+02:00</requestDate>
      <valid>true</valid>
      <name>John Doe</name>
      <address>123 Main St  </address>
    </checkVatResponse>
  </soap:Body>
</soap:Envelope>
"""
    invalid = success.replace("<valid>true</valid>", "<valid>false</valid>").replace(
        "<name>John Doe</name>", '<name>---</name>'
    )
    nil = success.replace("<name>John Doe</name>", '<name xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>')
    (dest / "synthetic_valid_true.xml").write_text(success, encoding="utf-8")
    (dest / "synthetic_valid_false.xml").write_text(invalid, encoding="utf-8")
    (dest / "synthetic_name_nil.xml").write_text(nil, encoding="utf-8")
    for fault in [
        "MS_MAX_CONCURRENT_REQ",
        "MS_MAX_CONCURRENT_REQ_TIME",
        "MS_UNAVAILABLE",
        "SERVICE_UNAVAILABLE",
        "TIMEOUT",
        "GLOBAL_MAX_CONCURRENT_REQ",
        "INVALID_INPUT",
    ]:
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Server</faultcode>
      <faultstring>{fault}</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>
"""
        (dest / f"synthetic_fault_{fault}.xml").write_text(xml, encoding="utf-8")
    print("wrote synthetic VIES fixtures")


def write_geolocate_fixture() -> None:
    """Success body is built from the captured countries row, not from the edge."""
    raw = (ROOT / "tests" / "fixtures" / "countries_body.json").read_text(encoding="utf-8")
    countries = json.loads(raw)
    ee = next(row for row in countries if row["iso2"] == "EE")
    # Preserve the production number tokens for coordinates.
    start = raw.find('{"iso2":"EE"')
    end = raw.find("},{", start)
    obj = raw[start:end]
    lat = obj.split('"latitude":', 1)[1].split(",", 1)[0]
    lon = obj.split('"longitude":', 1)[1].split(",", 1)[0]

    def string(value: str) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    body = (
        '{"iso2":"EE","iso3":"EST","country_code":"EE","name":'
        + string(ee["name"])
        + ',"numeric_code":'
        + str(ee["numeric_code"])
        + ',"phone_code":'
        + string(ee["phone_code"])
        + ',"capital":'
        + string(ee["capital"])
        + ',"currency":'
        + string(ee["currency"])
        + ',"tld":'
        + string(ee["tld"])
        + ',"region":'
        + string(ee["region"])
        + ',"subregion":'
        + string(ee["subregion"])
        + ',"latitude":'
        + lat
        + ',"longitude":'
        + lon
        + ',"emoji":'
        + string(ee["emoji"])
        + ',"ip":"203.0.113.10"}'
    )
    case = {
        "name": "geolocate_ee",
        "request": {
            "method": "GET",
            "path": "/geolocate",
            "headers": {"CF-IPCountry": "EE", "CF-Connecting-IP": "203.0.113.10"},
        },
        "status": 200,
        "headers": {"content-type": "application/json"},
        "body": body,
        "body_file": None,
        "note": "Synthesised from the production countries row. Not requested from the edge.",
    }
    missing = {
        "name": "geolocate_missing",
        "request": {"method": "GET", "path": "/geolocate", "headers": {}},
        "status": 404,
        "headers": {"content-type": "application/json"},
        "body": '{"detail":"Country code not received from CDN headers (CF-IPCountry or Cdn-RequestCountryCode)."}',
        "body_file": None,
    }
    unknown = {
        "name": "geolocate_unknown",
        "request": {"method": "GET", "path": "/geolocate", "headers": {"CF-IPCountry": "XX"}},
        "status": 404,
        "headers": {"content-type": "application/json"},
        "body": '{"detail":"Data for country code `XX` not found."}',
        "body_file": None,
    }
    bunny = {
        "name": "geolocate_bunny",
        "request": {
            "method": "GET",
            "path": "/geolocate",
            "headers": {"Cdn-RequestCountryCode": "EE"},
        },
        "status": 200,
        "headers": {"content-type": "application/json"},
        "body": body.replace('"ip":"203.0.113.10"', '"ip":null'),
        "body_file": None,
        "note": "Bunny header only. ip is null because CF-Connecting-IP is absent.",
    }
    dest = ROOT / "tests" / "golden"
    for item in (case, missing, unknown, bunny):
        (dest / f"{item['name']}.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print("wrote geolocate fixtures from countries row")


def main() -> int:
    hist = download(
        "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml",
        CACHE / "eurofxref-hist.xml",
    )
    hist90 = download(
        "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml",
        CACHE / "eurofxref-hist-90d.xml",
    )
    days = parse_hist(hist)
    print(f"ecb days={len(days)} {days[0][0]}..{days[-1][0]}")
    for name, method, path, headers, body_file in REQUESTS:
        for attempt in range(4):
            status, resp_headers, body = fetch(method, path, headers)
            if status != 429:
                break
            time.sleep(1.5)
        else:
            print(f"gave up after 429 on {path}", file=sys.stderr)
            return 1
        if status == 403 and b"1010" in body:
            print("cloudflare blocked the recorder", file=sys.stderr)
            return 1
        write_case(name, method, path, headers, status, resp_headers, body, body_file)
        time.sleep(SLEEP)
    write_excerpts(hist, hist90)
    write_vies_fixtures()
    write_geolocate_fixture()
    mismatches = compare_rates(days)
    if mismatches:
        print(f"{mismatches} rates goldens disagree with ECB history", file=sys.stderr)
        return 2
    print("rates goldens match ECB history")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
