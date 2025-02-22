web: gunicorn app:app --workers 4 --threads 2 --bind 0.0.0.0:3000
worker: celery -A app.celery worker --loglevel=info
