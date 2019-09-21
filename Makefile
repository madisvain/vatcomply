run:
	uvicorn app:app --reload

pip:
	pip install -r requirements.txt --upgrade

migrate:
	PYTHONPATH=.:$PYTHONPATH alembic upgrade head

test:
	export TESTING=True; pytest -s --disable-warnings
