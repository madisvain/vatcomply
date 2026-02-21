.PHONY: run pip freeze migrate migrations test coverage up down build

run:
	DEBUG=True uv run python manage.py runbolt --dev

pip:
	uv sync

freeze:
	uv lock

migrate:
	uv run python manage.py migrate

migrations:
	uv run python manage.py makemigrations

test:
	uv run pytest

coverage:
	uv run coverage run -m pytest && uv run coverage report -m

up:
	colima start && docker compose up --build

down:
	docker compose down && colima stop

build:
	docker compose build
