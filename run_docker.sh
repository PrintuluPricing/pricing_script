#! /usr/bin/env bash

. ./.env

docker run -p 5000:5000 -e MONGO_URI=$MONGO_URI -e REDIS_URL=$REDIS_URL -e DEBUG=$DEBUG pricing
