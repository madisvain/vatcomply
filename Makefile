run:
	export DEBUG=True; uvicorn vatcomply.asgi:application --reload

pip:
	pip install -r requirements.in --upgrade

migrate:
	python manage.py migrate

migrations:
	python manage.py makemigrations

test:
	python manage.py test --keepdb