from combine import create_combinations
from pricing import pricing_calculation
from pymongo import MongoClient
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone
import io
import pandas as pd


load_dotenv()
MONGO_URI = os.environ.get("MONGO_URI", "")
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
REDIS_URL = os.environ.get("REDIS_URL")

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
    client.admin.command('ping')
    logger.info("Successfully connected to MongoDB")
    db = client['Printulu']
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise

print("Mongo DB Connected")


def calculate_pricing_job(code):
    logger.info(f"Starting Job for Price Calculation {code}")
    combinations = create_combinations(code)
    logger.info("Created Combinations")
    buffer = io.StringIO()
    combinations.to_csv(buffer, index=False)
    buffer.seek(0)
    logger.info("Created Combinations and running Prices")
    try:
        (success_code, final_prices, final_prices_df) = pricing_calculation(buffer)
        if success_code == "success":
            logger.info("Pricing Finished, Saving to Database")
            logger.info(final_prices)
            final_prices = [{str(k): price[k] for k in price.keys()} for price in final_prices]
            prices_doc = {'product_code': code, 'prices': final_prices}
            version = get_last_version(code) + 1
            post_pricing(prices_doc, version)
            logger.info("Saved to MongoDB")
            logger.debug("Saving CSV File")
            logger.info(f"Saving csv file: ./prices/{code}_prices-{version}.csv")
            final_prices_df.to_csv(f"./prices/{code}_prices-{version}.csv", sep=";")
        else:
            logger.info(f"{code} generated no prices")
            collection = db["pricing_logs"]
            collection.insert_one({"timestamp": datetime.now(timezone.utc), "output":final_prices, "code":code})
            raise ValueError("No Data Calculated")

    except Exception as e:
        logger.error(f"{code} failed: {str(e)}")
        collection = db["pricing_logs"]
        collection.insert_one({"timestamp": datetime.now(timezone.utc), "error":str(e), "code":code})
        raise


def post_pricing(final_prices, version):
    pricing_collection = db['product_prices']
    final_prices["created_at"] = datetime.now(timezone.utc)
    final_prices["version"] = version
    pricing_collection.insert_one(final_prices)


def get_last_version(product_code):
    pricing_collection = db['product_prices']
    product_prices = list(pricing_collection.find({"product_code":product_code}))
    if len(product_prices) == 0:
        return 0
    product_prices.sort(key=lambda x:x.get("version",0) if x!= None else 0, reverse=True)
    last_version = product_prices[0]
    print(last_version)
    return last_version.get("version")


if __name__ == "__main__":
    pass
