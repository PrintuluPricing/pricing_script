from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import logging
from dotenv import load_dotenv
from rq import Queue
import redis
from tasks import calculate_pricing_job
import glob


load_dotenv()
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
REDIS_URL = os.environ.get("REDIS_URL","redis://127.0.0.1:6379")
os.environ['OPENBLAS_NUM_THREADS'] = '2'
redis_conn = redis.from_url(REDIS_URL)
queue = Queue(connection=redis_conn)


# Configure logging
log_level = logging.INFO

if DEBUG:
    log_level = logging.DEBUG

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

pymongo_logger = logging.getLogger('pymongo')
pymongo_logger.setLevel(logging.INFO)
app = Flask(__name__, static_folder='.')
CORS(app)


@app.route('/api/calculate/<code>', methods=['POST'])
def calculate_pricing(code):
    task = queue.enqueue(calculate_pricing_job, code, job_timeout=1500)
    return jsonify({"task_id": task.id}), 202


@app.route('/api/generate_pricing', methods=['POST'])
def generate_pricing():
    body = request.json
    product_code = body.get("product_code")
    user_email = body.get("user_email", "")
    task = queue.enqueue(calculate_pricing_job, product_code, job_timeout=1500)
    return jsonify({"task_id": task.id}), 202


@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    job = queue.fetch_job(task_id)
    if job is None:
        return jsonify({'error': 'Job not found'}), 404
    status = job.get_status()
    result = job.result  # This will be None if the job is not complete

    return jsonify({'status': status, 'result': result}), 200


@app.route('/api/files', methods=['GET'])
def get_files():
    files = glob.glob("./prices/*")

    return jsonify({'files': str(files)}), 200


@app.route('/api/download/<product_code>', methods=['GET'])
def download_prices(product_code):
    product_prices = glob.glob(f"./prices/{product_code}_prices-*.csv")
    product_prices.sort(key= lambda x: x.split("-")[1].split(".")[0], reverse=True)
    latest_file = product_prices[0].replace("./prices/","")
    directory = os.path.join(app.root_path, "prices")
    return send_from_directory(directory, latest_file, as_attachment=True)


@app.route('/api/download-all/', methods=['GET'])
def download_all_prices():
    files = glob.glob(".prices/*_prices-*.csv")
    all_prices_file = glob.glob(".prices/all-prices.csv")[0]

    return jsonify({'files': "Todo"}), 200
