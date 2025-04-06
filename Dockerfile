FROM python:3.11-slim-buster

WORKDIR /

RUN pip install --upgrade pip

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

# VOLUME /prices
EXPOSE 5000


COPY docker_entrypoint.sh docker_entrypoint.sh

RUN chmod +x docker_entrypoint.sh

CMD ["./docker_entrypoint.sh"]
