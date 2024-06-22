import pandas as pd
import numpy as np
import gspread
import re


key = "sheets_key_new.json"
service_acc = gspread.service_account(key)

# variables
categories_space = {
    "Litho": {"width": 15, "height": 5},
    "SF Digital": {"width": 1, "height": 1},
    "LF Digital": {"width": 5, "height": 5},
}

INPUT_PRICES_FOLDER = "1BrbtZ82ygpJ6Yu6m0nWboa2KN-rDe7PT"

placements = {}
BLEED = 3

cached_data = {}

def get_placements(format: str, size: str, category: str):
    x, y = get_dimensions(format)
    x = float(x) + BLEED
    y = float(y) + BLEED
    if category == "LF Digital":
        return 100 / x * 100 / y
    height, width = get_dimensions(size)
    height -= categories_space[category]["height"]
    width -= categories_space[category]["width"]
    placements1 = int(height/x * width / y)
    placements2 = int(height/y * width / x)
    placement = max(placements1, placements2)
    placements[format] = {size: placement}
    return placement


def get_dimensions(size: str) -> tuple[float, float]:
    size = size.replace("_", ".")
    height, width = re.findall(r"(\d*\.?\d+)\s?x\s?(\d*\.?\d+)",size)[0]
    height = float(height)
    width = float(width)
    return height, width


def get_SQM(format: str) -> float:
    height, width = get_dimensions(format)
    return height * width / 10_000


def read_google_sheet(folder: str, wb_name: str, sheet_name: str)-> pd.DataFrame :
    wb = service_acc.open(wb_name, folder)
    ws = wb.worksheet(sheet_name)
    values = ws.get_all_values()
    data = pd.DataFrame(values[1:], columns=values[0])
    return data


def get_nth_value(x: str, delim: str, n: int) -> str:
    return x.split(delim)[n]


def calculate_attributes(df: pd.DataFrame, finishing: pd.DataFrame)-> pd.DataFrame:
    finishing_costs = pd.merge(df[["Supplier", "Quantity", "Finishing", "Total Sheets"]], finishing, "left", left_on=["Supplier", "Finishing"], right_on=["Supplier", "Attribute"])
    finishing_costs["Finishing_costs"] = finishing_costs["Setup-Cost"] + np.where(finishing_costs["Calculation"] == "PI", finishing_costs["Quantity"] * finishing_costs["value"], finishing_costs["Total Sheets"] *finishing_costs["value"])
    # Extra Costs
    extra_costs = pd.merge(df[["Supplier", "Quantity", "Extra", "Total Sheets"]], finishing, "left", left_on=["Supplier", "Extra"], right_on=["Supplier", "Attribute"])
    extra_costs["Extra_costs"] = extra_costs["Setup-Cost"] + np.where(extra_costs["Calculation"] == "PI", extra_costs["Quantity"] * extra_costs["value"], extra_costs["Total Sheets"] *extra_costs["value"])
    # Binding Costs # TODO: Check Later how to calculate Wiro Biniding
    binding_costs = pd.merge(df[["Supplier", "Quantity", "Binding", "Total Sheets"]], finishing, "left", left_on=["Supplier", "Binding"], right_on=["Supplier", "Attribute"])
    binding_costs["Binding_costs"] = binding_costs["Setup-Cost"] + np.where(binding_costs["Calculation"] == "PI", binding_costs["Quantity"] * binding_costs["value"], binding_costs["Total Sheets"] *binding_costs["value"])
    # Refinement Costs
    refinement = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Refinement")
    refinement = pd.melt(refinement, id_vars="Refinement", var_name="Supplier", value_name="Refinement_costs")
    refinement = refinement[refinement["Refinement_costs"]!= "" ]
    refinement["Refinement_costs"] = pd.to_numeric(refinement["Refinement_costs"], errors="coerce")

    df = pd.merge(df, refinement, "left", on=["Supplier", "Refinement"])
    df["Refinement_costs"] = df["Refinement_costs"] * df["SQM"] * df["Total Sheets"]
    print(df)
    return df

def get_finishing_costs()-> pd.DataFrame:
    if "finishing" in cached_data.keys():
        return cached_data["finishing"]
    finishing = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Finishing")
    finishing = pd.melt(finishing , id_vars=["Attribute", "Calculation"], var_name="Supplier")
    finishing = finishing [finishing["value"] != ""]
    finishing["Setup-Cost"] = finishing ["value"].str.extract("(.*)\+")
    finishing["Setup-Cost"] = pd.to_numeric(finishing ["Setup-Cost"],errors="coerce")
    finishing["value"] = finishing["value"].str.replace(".*\+","",regex=True)
    finishing["/1000"] = finishing["value"].str.extract("(/\s?1000)")
    finishing["/1000"] = finishing["value"].str.contains("(/\s?1000)")
    finishing["value"] = finishing["value"].str.replace("(/\s?1000)","",regex=True)
    finishing["value"] = pd.to_numeric(finishing["value"], errors="coerce")
    finishing["value"] = np.where(finishing["/1000"], finishing["value"] / 1000 , finishing["value"])
    cached_data["finishing"] = finishing
    return finishing


def get_additional()-> tuple[pd.DataFrame, pd.DataFrame]:
    if "additional" in cached_data.keys():
        print("Loading Data from cached")
        return cached_data["additional"]
    additional_prices = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Fixed Price")
    additional_prices = pd.melt(additional_prices, var_name="Supplier", id_vars="Attribute")
    additional_prices = additional_prices[additional_prices["value"] != ""]
    additional_prices["value"] = additional_prices["value"].astype(float)
    additional_prices["Machine_size"] = additional_prices["Attribute"].str.extract(r"(A\d)")
    markup = additional_prices[additional_prices["Attribute"].str.contains("Markup")].reset_index(drop=True)
    markup = markup[["Supplier", "value"]].rename({"value": "Supplier Markup"},axis=1)
    cached_data["additional"] = additional_prices, markup
    return additional_prices, markup


def get_paper_costs()-> pd.DataFrame:
    if "paper" in cached_data.keys():
        return cached_data["paper"]
    paper_prices = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Paper Price")
    paper_prices = paper_prices[["Grammage", "Sheet_size", "Price incl 5%"]]
    paper_prices = paper_prices.rename({"Grammage": "Paper", "Price incl 5%": "Paper Costs"}, axis=1)
    paper_prices["Paper Costs"] = paper_prices["Paper Costs"].astype(float)
    cached_data["paper"] = paper_prices
    return paper_prices


def get_clicks()-> pd.DataFrame:
    if "clicks" in cached_data.keys():
        return cached_data["clicks"]
    clicks_costs = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Digital Clicks")
    clicks_costs = pd.melt(clicks_costs, "Attribute", var_name="Supplier", value_name="Clicks Cost")
    clicks_costs = clicks_costs[clicks_costs["Clicks Cost"]!= ""]
    clicks_costs["Machine_size"] = clicks_costs["Attribute"].str.extract(r"(A\d)")
    clicks_costs["Workstyle"] = clicks_costs["Attribute"].str.extract(r"\((.*)\)")
    clicks_costs["Clicks Cost"] = clicks_costs["Clicks Cost"].astype(float)
    clicks_costs = clicks_costs.drop("Attribute", axis=1)
    cached_data["clicks"] = clicks_costs
    return clicks_costs


def get_litho_machines()-> pd.DataFrame:
    if "litho_machines" in cached_data.keys():
        return cached_data["litho_machines"]
    litho_machines = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Machine Costs")
    litho_machines = pd.melt(litho_machines, ["Attribute", "Category"],var_name="Supplier")
    litho_machines = litho_machines[litho_machines["value"] != ""]
    litho_machines["value"] = litho_machines["value"].astype(float)
    litho_machines["Machine_size"] = litho_machines["Attribute"].str.extract(r"(A\d)")
    litho_machines = pd.pivot(litho_machines,columns="Category",values="value",index=["Machine_size","Supplier"]).reset_index()
    cached_data["litho_machines"] = litho_machines
    return litho_machines


if __name__ == "__main__":
    pass
