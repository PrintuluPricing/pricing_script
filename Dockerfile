FROM python:3.11-slim-buster

WORKDIR /

RUN pip install --upgrade pip

COPY requirements.txt requirements.txt

RUN apt-get update && apt-get install -y redis-server

RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
EXPOSE 6379


# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
CMD redis-server --daemonize yes --save "" && rq worker & gunicorn app:app -b :5000
