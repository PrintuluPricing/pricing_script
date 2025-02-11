from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson import json_util
import json
import os
import logging
from dotenv import load_dotenv


load_dotenv()
MONGO_URI = os.environ.get("MONGO_URI", "")
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Configure logging

log_level = logging.INFO

if DEBUG:
    log_level = logging.DEBUG

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


logger.debug(MONGO_URI)

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


@app.route('/api/attributes', methods=['GET'])
def get_attributes():
    try:
        attr_type = request.args.get('type')
        query = {}

        # Handle type-specific queries
        if attr_type:
            # Case-insensitive search for type
            query['type'] = {'$regex': f'^{attr_type}$', '$options': 'i'}
            logger.debug(f"Searching for type: {attr_type}")

        logger.debug(f"Final query: {query}")

        # Get attributes and sort them
        attributes = list(db.attributes.find(query).sort('name', 1))
        logger.debug(f"Found {len(attributes)} attributes")

        # Log the first few attributes for debugging
        if attributes:
            logger.debug(f"Sample attributes: {attributes[:2]}")

        return jsonify(parse_json(attributes))
    except Exception as e:
        logger.error(f"Error fetching attributes: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/attributes/by-category', methods=['POST'])
def get_attributes_by_category():
    try:
        data = request.json
        logger.debug(f"Received request data: {data}")

        attr_type = data.get('type')
        categories = data.get('categories', [])

        # Build the query
        query = {}

        # Add type filter (case-insensitive)
        if attr_type:
            query['type'] = {'$regex': f'^{attr_type}$', '$options': 'i'}

        # Add categories filter - only return attributes where ALL selected categories match
        if categories:
            # Use $all instead of $in to ensure ALL categories must match
            query['categories'] = {'$all': categories}

        logger.debug(f"MongoDB Query: {query}")

        # Get attributes and sort them
        attributes = list(db.attributes.find(query).sort('name', 1))
        logger.debug(f"Found {len(attributes)} attributes")

        if len(attributes) == 0:
            logger.debug(
                f"No attributes found for type {attr_type} and categories {categories}")
        else:
            # Log each attribute and its categories for debugging
            for attr in attributes:
                logger.debug(
                    f"Found attribute: {attr.get('name')} with categories: {attr.get('categories', [])}")

        return jsonify(parse_json(attributes))
    except Exception as e:
        logger.error(f"Error fetching attributes by category: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)
