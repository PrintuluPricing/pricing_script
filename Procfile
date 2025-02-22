web: gunicorn app:app --bind 0.0.0.0:$PORT && celery -A worker.celery worker --loglevel=info
