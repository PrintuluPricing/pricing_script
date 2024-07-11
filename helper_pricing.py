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


def get_placements(format: str, size: str, category: str) -> int | float:
    x, y = get_dimensions(format)
    x = float(x) + BLEED
    y = float(y) + BLEED
    if category == "LF Digital":
        return (100 / x * 100 / y)
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
    height, width = re.findall(r"(\d*\.?\d+)\s?x\s?(\d*\.?\d+)", size)[0]
    height = float(height)
    width = float(width)
    return height, width


def get_SQM(format: str) -> float:
    height, width = get_dimensions(format)
    return height * width / 10_000


def read_google_sheet(folder: str, wb_name: str, sheet_name: str) -> pd.DataFrame:
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
    finishing_costs["Finishing_costs"] = np.where(finishing_costs["Finishing"] == "None",0, finishing_costs["Finishing_costs"])
    # Extra Costs
    extra_costs = pd.merge(df[["Supplier", "Quantity", "Extra", "Total Sheets"]], finishing, "left", left_on=["Supplier", "Extra"], right_on=["Supplier", "Attribute"])
    extra_costs["Extra_costs"] = extra_costs["Setup-Cost"] + np.where(extra_costs["Calculation"] == "PI", extra_costs["Quantity"] * extra_costs["value"], extra_costs["Total Sheets"] *extra_costs["value"])
    extra_costs["Extra_costs"] = np.where(extra_costs["Extra"] == "None", 0, extra_costs["Extra_costs"])
    # Binding Costs # TODO: Check Later how to calculate Wiro Biniding
    binding_costs = pd.merge(df[["Supplier", "Quantity", "Binding", "Total Sheets"]], finishing, "left", left_on=["Supplier", "Binding"], right_on=["Supplier", "Attribute"])
    binding_costs["Binding_costs"] = binding_costs["Setup-Cost"] + np.where(binding_costs["Calculation"] == "PI", binding_costs["Quantity"] * binding_costs["value"], binding_costs["Total Sheets"] *binding_costs["value"])
    binding_costs["Binding_costs"] = np.where(binding_costs["Binding"] == "None", 0, binding_costs["Binding_costs"])
    # Refinement Costs
    refinement = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Refinement")
    refinement = pd.melt(refinement, id_vars="Refinement", var_name="Supplier", value_name="Refinement_costs")
    refinement = refinement[refinement["Refinement_costs"]!= "" ]
    refinement["Refinement_costs"] = pd.to_numeric(refinement["Refinement_costs"], errors="coerce")

    df["Finishing_costs"] = finishing_costs["Finishing_costs"]
    df["Binding_costs"] = binding_costs["Binding_costs"]
    df["Extra_costs"] = extra_costs["Extra_costs"]

    df = pd.merge(df, refinement, "left", on=["Supplier", "Refinement"])
    df["Refinement_costs"] = df["Refinement_costs"] * df["SQM"] * df["Total Sheets"]
    df["Refinement_costs"] = np.where(df["Refinement"] == "None", 0, df["Refinement_costs"])
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


def get_litho_machines() -> pd.DataFrame:
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


def get_lf_mahcines() -> pd.DataFrame:
    if "lf_machines" in cached_data.keys():
        return cached_data["lf_machines"]
    lf_machines = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "LF Printing")
    lf_machines = lf_machines.drop("Attribute", axis=1)
    lf_machines = pd.melt(lf_machines, ["Color", "Machine"], var_name="Supplier")
    lf_machines = lf_machines[lf_machines["value"] != ""]
    lf_machines["value"] = lf_machines["value"].astype(float)
    lf_machines = lf_machines.rename({"Color": "colors", "value": "Printing Rate"}, axis=1)
    cached_data["lf_machines"] = lf_machines
    return lf_machines


def get_lf_waste() -> pd.DataFrame:
    if "lf_waste" in cached_data.keys():
        return cached_data["lf_waste"]
    lf_waste = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "LF Waste")
    lf_waste = pd.melt(lf_waste, "Attribute", var_name="Supplier")
    lf_waste = lf_waste[lf_waste["value"] != ""]
    lf_waste["value"] = pd.to_numeric(lf_waste["value"])
    lf_waste = lf_waste.rename({"value": "Waste %", "Attribute": "Paper"}, axis=1)
    cached_data["lf_waste"] = lf_waste
    return lf_waste

def get_lf_double() -> list[str]:
    if "lf_double" in cached_data.keys():
        return cached_data["lf_double"]
    lf_double = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "LF Double")
    lf_double = list(lf_double["Product"])
    cached_data["lf_double"] = lf_double
    return lf_double


def get_lf_cutting() -> pd.DataFrame:
    if "lf_cutting" in cached_data.keys():
        return cached_data["lf_cutting"]
    lf_cutting = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "LF Cutting")
    lf_cutting = pd.melt(lf_cutting, "Attribute", var_name="Supplier")
    lf_cutting = lf_cutting[lf_cutting["value"] != ""]
    lf_cutting["value"] = pd.to_numeric(lf_cutting["value"])
    lf_cutting = lf_cutting.rename({"value": "LF Cutting", "Attribute": "Paper"}, axis=1)
    cached_data["lf_cutting"] = lf_cutting
    return lf_cutting


def get_lf_material() -> pd.DataFrame:
    if "lf_material" in cached_data.keys():
        return cached_data["lf_material"]
    lf_material = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "LF Material")
    lf_material = pd.melt(lf_material, "Attribute", var_name="Supplier")
    lf_material = lf_material[lf_material["value"] != ""]
    lf_material["value"] = pd.to_numeric(lf_material["value"])
    lf_material = lf_material.rename({"value": "LF Material", "Attribute": "Paper"}, axis=1)
    cached_data["lf_material"] = lf_material
    return lf_material


def get_lf_extra() -> pd.DataFrame:
    if "lf_extra" in cached_data.keys():
        return cached_data["lf_extra"]
    lf_extra = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "LF Extra")
    lf_extra = pd.melt(lf_extra, "Attribute", var_name="Supplier")
    lf_extra = lf_extra[lf_extra["value"] != ""]
    lf_extra["value"] = pd.to_numeric(lf_extra["value"])
    lf_extra = lf_extra.rename({"value": "LF Extra", "Attribute": "Extra"}, axis=1)
    cached_data["lf_extra"] = lf_extra
    return lf_extra


def get_wiro_pur_binding_costs() -> pd.DataFrame:
    if "wiro" in cached_data.keys():
        return cached_data["wiro"], cached_data["wiro_thickness"]
    binding_prices = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Binding")
    binding_prices = pd.melt(binding_prices, id_vars=["Attribute", "Length", "Setup"], var_name="Thickness")
    binding_prices = binding_prices[binding_prices["value"] != ""]
    #FIX: Check the filter laterrrrr!!!!
    binding_prices = binding_prices[binding_prices["Attribute"] == "Wiro"]
    binding_prices["value"] = pd.to_numeric(binding_prices["value"], errors="coerce")
    binding_prices["Setup"] = pd.to_numeric(binding_prices["Setup"], errors="coerce")
    cached_data["wiro"] = binding_prices
    binding_thickness = list(set(binding_prices["Thickness"]))
    binding_thickness = [float(thic) for thic in binding_thickness]
    binding_length = list(set(binding_prices["Length"]))
    binding_length = [float(thic) for thic in binding_length]
    cached_data["wiro_thickness"] = binding_thickness
    cached_data["wiro_length"] = binding_length
    return binding_prices, binding_thickness, binding_length


def get_wiro_thickness() -> pd.DataFrame:
    if "wiro_thickness" in cached_data.keys():
        return cached_data["wiro_thickness"]
    wiro_thickness = get_wiro_pur_binding_costs()[1]
    return wiro_thickness


def get_wiro_length() -> pd.DataFrame:
    if "wiro_length" in cached_data.keys():
        return cached_data["wiro_length"]
    wiro_length = get_wiro_pur_binding_costs()[1]
    return wiro_length


if __name__ == "__main__":
    pass
