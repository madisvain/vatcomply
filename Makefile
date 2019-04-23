run:
	uvicorn app:app --reload

test:
	pytest -s --disable-warnings