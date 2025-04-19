run:
	export DEBUG=True; uvicorn vatcomply.asgi:application --reload

pip:
	uv pip install -r requirements.in --upgrade

freeze:
	uv pip compile requirements.in -o requirements.txt && uv pip compile requirements.txt -o uv.lock

migrate:
	python manage.py migrate

migrations:
	python manage.py makemigrations

test:
	python manage.py test --keepdb

coverage:
	coverage run manage.py test --keepdb && coverage report -m
