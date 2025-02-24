from combine import create_combinations
from pricing import pricing_calculation
from pymongo import MongoClient
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone


load_dotenv()
MONGO_URI = os.environ.get("MONGO_URI", "")
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Configure logging
log_level = logging.INFO

if DEBUG:
    log_level = logging.DEBUG

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

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



def calculate_pricing_job(code):
    logger.info("Starting Job for Price Calculation")
    combinations = create_combinations(code)
    logger.info("Created Combinations")
    combinations.to_csv(f"{code}_combinations.csv", index=False)
    logger.info("Saved Combinations and running Prices")
    final_prices = pricing_calculation([f"{code}_combinations.csv"])
    logger.info("Pricing Finished, Saving to Database")
    post_pricing(final_prices)
    logger.info("Saved to MongoDB")


def post_pricing(final_prices):
    pricing_collection = db['product_prices']
    final_prices["created_at"] = datetime.now(timezone.utc)
    pricing_collection.insert_one(final_prices)
