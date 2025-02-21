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
from celery import Celery

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

# Celery configuration
app.config['CELERY_BROKER_URL'] = REDIS_URL
app.config['CELERY_RESULT_BACKEND'] = REDIS_URL

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

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


# Celery task for long-running process

@celery.task
def calculate_pricing_job(code):
    logger.debug(f"Starting Calculation for {code}")
    combinations = create_combinations(code)
    combinations.to_csv(f"{code}_combinations.csv", index=False)
    logger.debug(f"Created Combinations for {code}")
    final = pricing_calculation([f"{code}_combinations.csv"])
    final.to_csv("testing from app.csv")
    logger.debug(f"Final Pricing for {code}")
    return final.to_json(orient='records')


@app.route('/api/combine/<code>', methods=['POST'])
def calculate_pricing(code):
    # Enqueue the task with Celery
    task = calculate_pricing_job.delay(code)
    return jsonify({"task_id": task.id}), 202


@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = calculate_pricing_job.AsyncResult(task_id)
    if task.state == 'PENDING':
        return jsonify({"status": "pending"}), 200
    elif task.state == 'SUCCESS':
        return jsonify({"status": "success", "result": task.result}), 200
    elif task.state == 'FAILURE':
        return jsonify({"status": "failure", "error": str(task.result)}), 200
    else:
        return jsonify({"status": task.state}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)
