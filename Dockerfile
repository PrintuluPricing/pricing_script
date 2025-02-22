FROM python:3.11-slim-buster

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt requirements.txt


RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000


# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
CMD ["python", "app.py"]
