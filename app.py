from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
from dotenv import load_dotenv
from rq import Queue
import redis
from tasks import calculate_pricing_job
import subprocess


load_dotenv()
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
REDIS_URL = os.environ.get("REDIS_URL","redis://127.0.0.1:6379")
redis_conn = redis.from_url(REDIS_URL)
queue = Queue(connection=redis_conn)


# Configure logging
log_level = logging.INFO

if DEBUG:
    log_level = logging.DEBUG

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
CORS(app)


@app.route('/api/calculate/<code>', methods=['POST'])
def calculate_pricing(code):
    task = queue.enqueue(calculate_pricing_job, code)
    logger.info(f"Task Started for {code}")
    subprocess.Popen(["rq", "worker"])
    logger.info("subprocess started")
    return jsonify({"task_id": task.id}), 202


@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    job = queue.fetch_job(task_id)
    if job is None:
        return jsonify({'error': 'Job not found'}), 404
    status = job.get_status()
    result = job.result  # This will be None if the job is not complete

    return jsonify({'status': status, 'result': result}), 200
