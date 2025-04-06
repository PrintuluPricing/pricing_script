#!/bin/bash
rq worker &
gunicorn app:app -b :5000
