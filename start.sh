#!/bin/sh
set -e

echo "[start.sh] Python: $(which python)"
echo "[start.sh] uv: $(which uv)"

# Run migrations and load data (skipped when using docker-compose, which has a dedicated migrate service)
if [ "${SKIP_MIGRATIONS:-false}" = "false" ]; then
    echo "[start.sh] Running migrations..."
    python manage.py migrate --noinput
    echo "[start.sh] Starting background data loading..."
    (python manage.py load_countries; python manage.py load_rates --last-90-days) &
fi

echo "[start.sh] Starting server on port ${PORT:-8000}..."
exec python manage.py runbolt --host 0.0.0.0 --port ${PORT:-8000}
