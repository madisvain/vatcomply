#!/bin/sh
set -e

# Run migrations and load data (skipped when using docker-compose, which has a dedicated migrate service)
if [ "${SKIP_MIGRATIONS:-false}" = "false" ]; then
    uv run --no-sync python manage.py migrate --noinput
    # Load data in background so server can start accepting connections immediately
    (uv run --no-sync python manage.py load_countries; uv run --no-sync python manage.py load_rates --last-90-days) &
fi

# Start web server (use PORT env var if set, default to 8000)
exec uv run --no-sync python manage.py runbolt --host 0.0.0.0 --port ${PORT:-8000}
