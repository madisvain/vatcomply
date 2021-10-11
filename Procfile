web: gunicorn app:app --worker-class uvicorn.workers.UvicornWorker --workers ${WEB_CONCURRENCY} --worker-tmp-dir /dev/shm --max-requests 1000
release: alembic upgrade head