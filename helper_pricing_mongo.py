import pandas as pd
import numpy as np
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import re
import logging


pymongo_logger = logging.getLogger('pymongo')
pymongo_logger.setLevel(logging.INFO)

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
        return height * width / 10_000
    height, width = get_dimensions(sheet_size)
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
    clicks_costs = clicks_costs.rename({"workstyle": "Workstyle", "price": "clicks_cost"}, axis=1)
    clicks_costs["clicks_cost"] = clicks_costs["clicks_cost"].astype("float16")
    clicks_costs["fixed_price"] = clicks_costs["fixed_price"].astype("float16")
    clicks_costs = clicks_costs[clicks_costs["supplier"].isin(REMOVED_SUPPLIERS) == False]
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
    litho_machines[["cost_per_hour", "plates_cost", "setup_time", "sheets_per_hour","fixed_price", "markup_percentage"]] = litho_machines[["cost_per_hour", "plates_cost", "setup_time", "sheets_per_hour","fixed_price", "markup_percentage"]].astype('float16')
    cached_data["litho_machines"] = litho_machines
    return litho_machines


def get_paper_costs()-> pd.DataFrame:
    if "paper" in cached_data.keys():
        return cached_data["paper"]
    paper_collection = db["paper_prices"]
    paper_prices = pd.DataFrame(list(paper_collection.find()))
    paper_prices = paper_prices.drop(["_id"], axis=1)
    paper_prices = paper_prices[["paper", "price", "sheet_size"]]
    paper_prices = paper_prices.rename({"paper": "Paper", "price": "Paper Costs"}, axis=1)
    paper_prices["Paper Costs"] = paper_prices["Paper Costs"].astype(float)
    cached_data["paper"] = paper_prices
    return paper_prices


def get_lf_mahcines() -> pd.DataFrame:
    if "lf_machines" in cached_data.keys():
        return cached_data["lf_machines"]
    lf_machines_collection = db["lf_machines_prices"]
    lf_machines = pd.DataFrame(list(lf_machines_collection.find()))
    lf_machines = lf_machines.drop(["_id"], axis=1)
    lf_machines = lf_machines.drop("attribute", axis=1)
    lf_machines = lf_machines.rename({"price": "Printing Rate"}, axis=1)
    lf_machines = lf_machines[lf_machines["supplier"].isin(REMOVED_SUPPLIERS) == False]
    lf_machines[["supplier", "colour", "machine"]] = lf_machines[["supplier", "colour", "machine"]].astype("category")
    lf_machines["Printing Rate"] = lf_machines["Printing Rate"].astype("float16")
    cached_data["lf_machines"] = lf_machines
    return lf_machines


def get_lf_material() -> pd.DataFrame:
    if "lf_material" in cached_data.keys():
        return cached_data["lf_material"]
    lf_material_collection = db["lf_material_prices"]
    lf_material = pd.DataFrame(list(lf_material_collection.find()))
    lf_material = lf_material.drop(["_id"], axis=1)
    lf_material = lf_material.rename({"gsm": "GSM"}, axis=1)
    lf_material["price"] = pd.to_numeric(lf_material["price"]).astype("float16")
    lf_material["GSM"] = pd.to_numeric(lf_material["GSM"]).astype("float16")
    lf_material["cutting"] = pd.to_numeric(lf_material["cutting"]).astype("float16")
    lf_material = lf_material.rename({"price": "LF Material", "attribute": "Paper", "waste": "Waste %", "cutting": "LF Cutting"}, axis=1)
    lf_material = lf_material[lf_material["supplier"].isin(REMOVED_SUPPLIERS) == False]
    lf_material[["supplier", "Paper"]] = lf_material[["supplier", "Paper"]].astype("category")
    cached_data["lf_material"] = lf_material
    return lf_material


def get_lf_extra() -> pd.DataFrame:
    if "lf_extra" in cached_data.keys():
        return cached_data["lf_extra"]
    collection = db["lf_extra_prices"]
    lf_extra = pd.DataFrame(list(collection.find()))
    lf_extra = lf_extra.drop(["_id"], axis=1)
    lf_extra["price"] = pd.to_numeric(lf_extra["price"]).astype("float16")
    lf_extra = lf_extra.rename({"price": "LF Extra", "attribute": "Extra"}, axis=1)
    lf_extra = lf_extra[lf_extra["supplier"].isin(REMOVED_SUPPLIERS) == False]
    lf_extra[["supplier", "Extra"]] = lf_extra[["supplier", "Extra"]].astype("category")
    cached_data["lf_extra"] = lf_extra
    return lf_extra


def get_lf_refinement() -> pd.DataFrame:
    if "lf_refinement" in cached_data.keys():
        return cached_data["lf_refinement"]
    collection = db["lf_refinement_prices"]
    lf_refinement = pd.DataFrame(list(collection.find()))
    lf_refinement = lf_refinement.drop(["_id"], axis=1)
    lf_refinement["price"] = pd.to_numeric(lf_refinement["price"]).astype("float16")
    lf_refinement = lf_refinement.rename({"price": "LF Refinement","attribute":"Refinement"}, axis=1)
    lf_refinement = lf_refinement[lf_refinement["supplier"].isin(REMOVED_SUPPLIERS) == False]
    lf_refinement[["supplier", "Refinement"]] = lf_refinement[["supplier", "Refinement"]].astype("category")
    cached_data["lf_refinement"] = lf_refinement
    return lf_refinement


def get_weights() -> pd.DataFrame:
    if "weights" in cached_data.keys():
        return cached_data["weights"]
    collection = db["attributes"]
    weights = pd.DataFrame(list(collection.find()))
    weights = weights.drop(["_id", "code", "categories"], axis=1)
    weights = weights.rename({"name": "Attribute", "type": "Type"}, axis=1)
    weights = weights[weights["GSM"] != ""].reset_index(drop=True)
    weights["GSM"] = pd.to_numeric(weights["GSM"]).astype("float16")
    weights[["Attribute", "Type"]] = weights[["Attribute", "Type"]].astype("category")
    cached_data["weights"] = weights
    return weights


def get_shipping_costs() -> pd.DataFrame:
    if "shipping" in cached_data.keys():
        return cached_data["shipping"]
    collection = db["shipping_prices"]
    shipping = pd.DataFrame(list(collection.find()))
    shipping = shipping.drop(["_id"], axis=1)
    shipping = shipping[shipping["destination"] == "National"]
    shipping[["minimum_cost", "minimum_kg", "kg_after"]] = shipping[["minimum_cost", "minimum_kg", "kg_after"]].astype('float32')
    cached_data["shipping"] = shipping
    return shipping


def get_litho_utilization()-> pd.DataFrame:
    if "litho_utilization" in cached_data.keys():
        return cached_data["litho_utilization"]
    collection = db["litho_utilization"]
    litho_utilization = pd.DataFrame(list(collection.find()))
    litho_utilization = litho_utilization.drop(["_id"], axis=1)
    litho_utilization["utilization"] = pd.to_numeric(litho_utilization["utilization"], errors="coerce").astype("float16")
    litho_utilization = litho_utilization.rename({"paper": "Paper", "paper_code": "Paper Code"}, axis=1)
    litho_utilization[["sheet_size", "Paper", "Paper Code"]] = litho_utilization[["sheet_size", "Paper", "Paper Code"]].astype("category")
    cached_data["litho_utilization"] = litho_utilization
    return litho_utilization


def get_finishing() -> pd.DataFrame:
    if "finishing" in cached_data.keys():
        return cached_data["finishing"]
    collection = db["finishing_prices"]
    finishing = pd.DataFrame(list(collection.find()))
    finishing = finishing.drop("_id", axis=1)
    cached_data["finishing"] = finishing
    return finishing


def get_extra() -> pd.DataFrame:
    if "extra" in cached_data.keys():
        return cached_data["extra"]
    collection = db["extra_prices"]
    extra = pd.DataFrame(list(collection.find()))
    extra = extra.drop("_id", axis=1)
    cached_data["extra"] = extra
    return extra


def get_binding() -> pd.DataFrame:
    if "binding" in cached_data.keys():
        return cached_data["binding"]
    collection = db["binding_prices"]
    binding = pd.DataFrame(list(collection.find()))
    binding = binding.drop("_id", axis=1)
    cached_data["binding"] = binding
    return binding


def get_refinement() -> pd.DataFrame:
    if "refinement" in cached_data.keys():
        return cached_data["refinement"]
    collection = db["refinement_prices"]
    refinement = pd.DataFrame(list(collection.find()))
    refinement = refinement.drop("_id", axis=1)
    refinement["price"] = refinement["price"].astype("float16")
    refinement = refinement.rename({"attribute": "Refinement"}, axis=1)
    cached_data["refinement"] = refinement
    return refinement


def calculate_attributes(df: pd.DataFrame) -> pd.DataFrame:
    finishing, refinement, binding, extra = get_finishing(), get_refinement(), get_binding(), get_extra()
    # Index(['supplier', 'attribute', 'attribute_code', 'price', 'setup'], dtype='object')
    df = df.reset_index(drop=True)

    print("Calculating Attributes: ", len(df))

    # FINISHING COSTS
    print("Finishing")

    finishing_costs = pd.merge(df[["supplier", "Quantity", "Finishing", "Total Sheets"]], finishing, "left", left_on=["supplier", "Finishing"], right_on=["supplier", "attribute"])
    finishing_costs["Finishing_costs"] = finishing_costs["setup"].fillna(0) +np.where(finishing_costs["price"] > 0,FIXED_FINISHING_HANDLING, 0)  + np.where(finishing_costs["calculation"] == "PI", finishing_costs["Quantity"] * finishing_costs["price"], finishing_costs["Total Sheets"] * finishing_costs["price"])
    finishing_costs["Finishing_costs"] = np.where(finishing_costs["Finishing"] == "None",0, finishing_costs["Finishing_costs"])

    print("Extra")
    # Extra Costs
    extra_costs = pd.merge(df[["supplier", "Quantity", "Extra", "Total Sheets"]],extra , "left", left_on=["supplier", "Extra"], right_on=["supplier", "attribute"])
    # NOTE: Check later which cases that apply to: Drilling, holes, should be applied as minimum handling fees

    extra_costs["Extra_costs"] = extra_costs["setup"].fillna(0) + np.where(extra_costs["price"] > 0,FIXED_EXTRA_HANDLING, 0) + np.where(extra_costs["calculation"] == "PI", extra_costs["Quantity"] * extra_costs["price"], extra_costs["Total Sheets"] * extra_costs["price"])
    extra_costs["Extra_costs"] = np.where(extra_costs["Extra"] == "None", 0, extra_costs["Extra_costs"])

    print("Binding")
    # Binding Costs

    binding_costs = pd.merge(df[["supplier", "Quantity", "Binding", "Total Sheets"]],binding , "left", left_on=["supplier", "Binding"], right_on=["supplier", "attribute"])
    binding_costs["Binding_costs"] = binding_costs["setup"].fillna(0) + np.where(binding_costs["calculation"] == "PI", binding_costs["Quantity"] * binding_costs["price"], binding_costs["Total Sheets"] *binding_costs["price"])
    binding_costs["Binding_costs"] = np.where(binding_costs["Binding"] == "None", 0, binding_costs["Binding_costs"])

    df["Finishing_costs"] = finishing_costs["Finishing_costs"]
    df["Binding_costs"] = np.where(df["Binding_costs"]> 0, df["Binding_costs"], binding_costs["Binding_costs"])
    df["Extra_costs"] = extra_costs["Extra_costs"]

    del (finishing_costs)
    del (binding_costs)
    del (extra_costs)

    print("Refinement")
    # Refinement Costs

    df = df.reset_index(drop=True)
    df = pd.merge(df, refinement, "left", on=["supplier", "Refinement"])
    df["Refinement_costs"] = df["price"] * df["SQM"] * df["Total Sheets"]
    df["Refinement_costs"] = np.where(df["Refinement_costs"]> 0, df["Refinement_costs"] + FIXED_REFINEMENT_HANDLING, 0)
    df["Refinement_costs"] = np.where(df["Refinement"] == "None", 0, df["Refinement_costs"])

    df["Refinement Costs"] = df["Refinement_costs"] * ( 1 + df["Refinement Markup"] /100)
    df["Extra Costs"] = df["Extra_costs"] * (1 + df["Extra Markup"] /100)
    df["Binding Costs"] = df["Binding_costs"] *(1 + df["Binding Markup"] /100)
    df["Finishing Costs"] = df["Finishing_costs"] *(1 + df["Finishing Markup"] /100)
    df["Total Printing Costs"] = df["Printing and Paper incl Markup"] * (1 + df["Printing Markup"] /100)

    print("Finished Attributes: ", len(df))
    df = df.reset_index(drop=True)
    return df


def get_wiro() -> tuple[pd.DataFrame, list[float], list[float]]:
    if "wiro" in cached_data.keys():
        return cached_data["wiro"], cached_data["wiro_thickness"], cached_data["wiro_length"]
    collection = db["wiro_bindings"]
    wiro_prices = pd.DataFrame(list(collection.find()))
    wiro_prices = wiro_prices.drop("_id", axis=1)
    # wiro_prices["length"] = pd.to_numeric(wiro_prices["length"])
    # wiro_prices["thickness"] = pd.to_numeric(wiro_prices["thickness"])
    wiro_prices["price"] = pd.to_numeric(wiro_prices["price"])
    wiro_prices["setup"] = pd.to_numeric(wiro_prices["setup"])
    wiro_length = list(set(wiro_prices["length"]))
    wiro_thickness = list(set(wiro_prices["thickness"]))
    cached_data["wiro"] = wiro_prices
    cached_data["wiro_length"] = wiro_length
    cached_data["wiro_thickness"] = wiro_thickness
    return wiro_prices, wiro_length, wiro_thickness


def get_hanger() -> tuple[pd.DataFrame, list[float], list[float]]:
    if "hanger" in cached_data.keys():
        return cached_data["hanger"], cached_data["hanger_thickness"], cached_data["hanger_length"]
    collection = db["hanger_bindings"]
    hanger_prices = pd.DataFrame(list(collection.find()))
    hanger_prices = hanger_prices.drop("_id", axis=1)
    # hanger_prices["length"] = pd.to_numeric(hanger_prices["length"])
    # hanger_prices["thickness"] = pd.to_numeric(hanger_prices["thickness"])
    hanger_prices["price"] = pd.to_numeric(hanger_prices["price"])
    hanger_prices["setup"] = pd.to_numeric(hanger_prices["setup"])
    hanger_length = list(set(hanger_prices["length"]))
    hanger_thickness = list(set(hanger_prices["thickness"]))
    cached_data["hanger"] = hanger_prices
    cached_data["hanger_length"] = hanger_length
    cached_data["hanger_thickness"] = hanger_thickness
    return hanger_prices, hanger_length, hanger_thickness


def get_pur() -> tuple[pd.DataFrame, list[float], list[float]]:
    if "pur" in cached_data.keys():
        return cached_data["pur"], cached_data["pur_thickness"], cached_data["pur_quantity"]
    collection = db["pur_bindings"]
    pur_prices = pd.DataFrame(list(collection.find()))
    pur_prices = pur_prices.drop("_id", axis=1)
    # pur_prices["quantity"] = pd.to_numeric(pur_prices["quantity"])
    # pur_prices["thickness"] = pd.to_numeric(pur_prices["thickness"])
    pur_prices["price"] = pd.to_numeric(pur_prices["price"])
    pur_prices["setup"] = pd.to_numeric(pur_prices["setup"])
    pur_quantity = list(set(pur_prices["quantity"]))
    pur_thickness = list(set(pur_prices["thickness"]))
    cached_data["pur_quantity"] = pur_quantity
    cached_data["pur"] = pur_prices
    cached_data["pur_thickness"] = pur_thickness
    return pur_prices, pur_quantity, pur_thickness


def get_wiro_thickness() -> list[float]:
    if "wiro_thickness" in cached_data.keys():
        return cached_data["wiro_thickness"]
    wiro_thickness = get_wiro()[2]
    cached_data["wiro_thickness"] = wiro_thickness
    return wiro_thickness


def get_wiro_length() -> list[float]:
    if "wiro_length" in cached_data.keys():
        return cached_data["wiro_length"]
    wiro_length = get_wiro()[1]
    cached_data["wiro_length"] = wiro_length
    return wiro_length


def get_pur_thickness() -> list[float]:
    if "pur_thickness" in cached_data.keys():
        return cached_data["pur_thickness"]
    pur_thickness = get_pur()[2]
    cached_data["pur_thickness"] = pur_thickness
    return pur_thickness


def get_pur_quantity() -> list[float]:
    if "pur_quantity" in cached_data.keys():
        return cached_data["pur_quantity"]
    pur_quantity = get_pur()[1]
    cached_data["pur_quantity"] = pur_quantity
    return pur_quantity


def get_hanger_length() -> list[float]:
    if "hanger_length" in cached_data.keys():
        return cached_data["hanger_length"]
    hanger_length = get_hanger()[1]
    cached_data["hanger_length"] = hanger_length
    return hanger_length


def get_custom() -> pd.DataFrame:
    if "custom" in cached_data.keys():
        return cached_data["custom"]
    collection = db["custom_prices"]
    custom = pd.DataFrame(list(collection.find()))
    custom = custom.drop("_id", axis=1)
    custom[["unit_price", "unit_kg", "setup"]] = custom[["unit_price", "unit_kg", "setup"]].astype(float)
    cached_data["custom"] = custom
    return custom


if __name__ == "__main__":
    pass
