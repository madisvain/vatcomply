run:
	uvicorn app:app --reload

pip:
	pip install -r requirements.txt --upgrade

migrate:
	PYTHONPATH=.:$PYTHONPATH alembic upgrade head

test:
	pytest -s --disable-warnings
