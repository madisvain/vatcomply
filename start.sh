#!/bin/sh
set -e

# Run migrations and load data (skipped when using docker-compose, which has a dedicated migrate service)
if [ "${SKIP_MIGRATIONS:-false}" = "false" ]; then
    python manage.py migrate --noinput
    python manage.py load_countries
    python manage.py load_rates --last-90-days
fi

# Start web server (use PORT env var if set, default to 8000)
exec python manage.py runbolt --host 0.0.0.0 --port ${PORT:-8000}
