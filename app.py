from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson import json_util
import json
import os
import logging
from dotenv import load_dotenv
from combine import create_combinations
from pricing import main


load_dotenv()
MONGO_URI = os.environ.get("MONGO_URI", "")
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

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


@app.route('/')
def serve_static():
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def serve_file(path):
    return send_from_directory('.', path)


@app.route('/api/db/connect', methods=['POST'])
def connect_db():
    try:
        client.admin.command('ping')
        return jsonify({'message': 'Connected to MongoDB successfully'})
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/combine/<code>', methods=['POST'])
def get_attributes_by_category(code):
    logger.debug(f"Starting Calculation for {code}")
    combinations = create_combinations(code)
    combinations.to_csv(f"{code}_combinations.csv", index=False)
    logger.debug(f"Created Combinations for {code}")
    final = main([f"{code}_combinations.csv"])
    logger.debug(f"Final Pricing for {code}")
    return final.to_json(orient='records')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)
