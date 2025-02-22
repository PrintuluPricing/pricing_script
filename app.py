from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import json_util
import json
import os
import logging
from dotenv import load_dotenv
from rq import Queue
import redis
from tasks import calculate_pricing_job


load_dotenv()
MONGO_URI = os.environ.get("MONGO_URI", "")
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
connection = redis.Connection(REDIS_URL)
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

# MongoDB connection
try:
    logger.info("Connecting to MongoDB...")
    client = MongoClient(MONGO_URI)
    # Test connection
    client.admin.command('ping')
    logger.info("Successfully connected to MongoDB")
    db = client['Printulu']
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise


def parse_json(data):
    return json.loads(json_util.dumps(data))


@app.route('/api/db/connect', methods=['POST'])
def connect_db():
    try:
        client.admin.command('ping')
        return jsonify({'message': 'Connected to MongoDB successfully'})
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/combine/<code>', methods=['POST'])
def calculate_pricing(code):
    task = queue.enqueue(calculate_pricing_job, code)
    logger.info("Task Started for ", code)
    return jsonify({"task_id": task.id}), 202


@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_status(job_id):
    job = queue.fetch_job(job_id)
    if job is None:
        return jsonify({'error': 'Job not found'}), 404
    status = job.get_status()
    result = job.result  # This will be None if the job is not complete

    return jsonify({'status': status, 'result': result}), 200
