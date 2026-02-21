# syntax=docker/dockerfile:1

# Build stage - includes build tools
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files and install
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code and collect static files
COPY . .
RUN SECRET_KEY=build-only uv run --no-sync python manage.py collectstatic --noinput


# Runtime stage - minimal image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

WORKDIR /app

# Copy app (including .venv) from builder
COPY --from=builder /app /app

# Setup cron (must be owned by root — cron service overrides USER below)
COPY crontab /etc/cron.d/vatcomply-cron
RUN chmod 0644 /etc/cron.d/vatcomply-cron && \
    crontab /etc/cron.d/vatcomply-cron && \
    touch /var/log/cron.log

# Make startup script executable
RUN chmod +x /app/start.sh

# Create non-root user for the web service
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["/app/start.sh"]
