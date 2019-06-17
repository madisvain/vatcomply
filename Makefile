run:
	uvicorn app:app --reload

pip:
	pip install -r requirements.txt --upgrade

test:
	pytest -s --disable-warnings