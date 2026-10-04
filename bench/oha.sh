#!/bin/sh
# Load-test the cached GET endpoints against a local server.
# Not a CI gate. Install oha: https://github.com/hatoo/oha
#
#   PORT=8000 ./bench/oha.sh
set -eu
PORT="${PORT:-8000}"
BASE="http://127.0.0.1:${PORT}"
if ! command -v oha >/dev/null 2>&1; then
  echo "oha is not installed" >&2
  exit 1
fi
for path in /rates /countries /vat_rates /currencies; do
  echo "== ${path}"
  oha -n 2000 -c 32 --no-tui "${BASE}${path}"
done
