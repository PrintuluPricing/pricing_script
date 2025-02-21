from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson import json_util
import json
import os
import logging
from dotenv import load_dotenv
from combine import create_combinations
from pricing import pricing_calculation
import pika
from redis import Redis
from rq import Queue
from rq.job import Job
from worker import conn  # Import the Redis connection from worker.py

load_dotenv()
MONGO_URI = os.environ.get("MONGO_URI", "")
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

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

# Redis connection for RQ
redis_conn = Redis.from_url(REDIS_URL)
q = Queue(connection=redis_conn)  # Create a queue

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

# Function to handle the long-running task
def calculate_pricing(code):
    logger.debug(f"Starting Calculation for {code}")
    combinations = create_combinations(code)
    combinations.to_csv(f"{code}_combinations.csv", index=False)
    logger.debug(f"Created Combinations for {code}")
    final = pricing_calculation([f"{code}_combinations.csv"])
    final.to_csv("testing from app.csv")
    logger.debug(f"Final Pricing for {code}")
    return final.to_json(orient='records')

@app.route('/api/combine/<code>', methods=['POST'])
def get_attributes_by_category(code):
    # Enqueue the job
    job = q.enqueue(calculate_pricing, code)
    return jsonify({"job_id": job.get_id()}), 202

@app.route('/api/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    job = Job.fetch(job_id, connection=redis_conn)
    if job.is_finished:
        return jsonify({"status": "finished", "result": job.result}), 200
    elif job.is_failed:
        return jsonify({"status": "failed", "error": str(job.exc_info)}), 200
    else:
        return jsonify({"status": "in_progress"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)
