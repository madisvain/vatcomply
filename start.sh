#!/bin/sh
set -e

# Run migrations and load data
uv run python manage.py migrate --noinput
uv run python manage.py load_countries
uv run python manage.py load_rates --last-90-days

# Start cron in background
cron

# Start web server
exec uv run python manage.py runbolt --host 0.0.0.0 --port 8000
