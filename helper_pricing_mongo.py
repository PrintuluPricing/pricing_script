import pandas as pd
import numpy as np
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

KEY = "sheets_key_new.json"

REMOVED_SUPPLIERS = ["DigitalSplash"]
FIXED_EXTRA_HANDLING = 75  # R75 to be added to all extras
FIXED_REFINEMENT_HANDLING = 50  # R50 to be added to all extras
FIXED_FINISHING_HANDLING = 25  # R25 to be added to all extras
COLOR_MAP = {"Full Colour": 4, "Black": 1}
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["Printulu"]

# variables
categories_space = {
    "Litho": {"width": 1.5, "height": 0.5},
    "SF Digital": {"width": 0.1, "height": 0.1},
    "LF Digital": {"width": 0.5, "height": 0.5},
}

INPUT_PRICES_FOLDER = "1BrbtZ82ygpJ6Yu6m0nWboa2KN-rDe7PT"

placements = {}
BLEED = 0.3

NO_PRICES_EXTRAS = ["None", "A2 - Calendar Option - Black Changes Only"]


cached_data = {}
cached_data["dimensions"] = {}


def get_placements(format: str, size: str, category: str) -> int | float:
    x, y = get_dimensions(format)
    x = float(x) + BLEED
    y = float(y) + BLEED
    if category == "LF Digital":
        return (100 / x * 100 / y)
    [height, width] = get_dimensions(size)
    height -= categories_space[category]["width"]
    width -= categories_space[category]["height"]
    placements1 = int(height/x) * int(width / y)
    placements2 = int(height/y) * int(width / x)
    placement = max(placements1, placements2)
    placements[format] = {size: placement}
    return placement


def get_dimensions(size: str) -> tuple[float, float]:
    if size in cached_data["dimensions"].keys():
        return cached_data["dimensions"][size]
    size = str(size).replace("format_", "")
    size = str(size).replace("_", ".")
    try:
        height, width = re.findall(r"(\d*\.?\d+)\s?x\s?(\d*\.?\d+)", size)[0]
    except:
        height, width = 1, 1
    height1 = float(height)
    width1 = float(width)
    # NOTE:
    # portrait height > width
    # landscape width > height
    # Potrait vs landscape => Height or width gets multiplied by 2 for open size
    height, width = height1, width1
    if "l" in size:
        height = min(height1, width1)
        width = max(height1, width1) * 2
    if "p" in size:
        height = max(height1, width1)
        width = min(height1, width1) * 2
    cached_data["dimensions"][size] = (height, width)
    return height, width


def get_litho_sf_SQM(sheet_size: str) -> float:
    height, width = get_dimensions(sheet_size)
    return height * width / 10_000


def get_lf_SQM(format: str) -> float:
    height, width = get_dimensions(format)
    return 100 / height * 100 / width

def get_SQM_df(format: str, sheet_size: str, category: str) -> pd.Series:
    if category == "LF Digital":
        height, width = get_dimensions(format)
        print("Worked LF Digital")
        return height * width / 10_000
    height, width = get_dimensions(sheet_size)
    print("Worked Other")
    return height * width / 10_000


def get_nth_value(x: str, delim: str, n: int) -> str:
    return x.split(delim)[n]


def get_clicks()-> pd.DataFrame:
    if "clicks" in cached_data.keys():
        return cached_data["clicks"]
    clicks_collection = db["sf_digital_machines_prices"]
    documents = clicks_collection.find()
    clicks_costs = pd.DataFrame(list(documents))
    clicks_costs = clicks_costs.drop(["_id"], axis=1)
    clicks_costs["front_colour"] = clicks_costs["colour"].map(COLOR_MAP)
    clicks_costs["back_colour"] = np.where(clicks_costs["workstyle"] == "Simplex", 0, clicks_costs["front_colour"])
    # clicks_costs = clicks_costs.drop(["Attribute", "Color"], axis=1)
    # clicks_costs = clicks_costs[clicks_costs["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    cached_data["clicks"] = clicks_costs
    return clicks_costs


def get_litho_machines() -> pd.DataFrame:
    if "litho_machines" in cached_data.keys():
        return cached_data["litho_machines"]

    litho_machines_collection = db["litho_machines_prices"]
    litho_machines = pd.DataFrame(list(litho_machines_collection.find()))
    litho_machines = litho_machines.drop(["_id"], axis=1)
    litho_machines = litho_machines[litho_machines["supplier"].isin(REMOVED_SUPPLIERS) == False]
    litho_machines[["supplier", "machine"]] = litho_machines[["supplier", "machine"]].astype("category")
    litho_machines[["cost_per_hour", "plates_cost", "setup_time", "sheets_per_hour"]] = litho_machines[["cost_per_hour", "plates_cost", "setup_time", "sheets_per_hour"]].astype('float16')
    cached_data["litho_machines"] = litho_machines
    return litho_machines


if __name__ == "__main__":
    pass
    litho = get_litho_machines()
    print(litho["fixed_price"])
