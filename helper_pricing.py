import pandas as pd
import numpy as np
import gspread
import re


KEY = "sheets_key_new.json"
service_acc = gspread.service_account(KEY)

REMOVED_SUPPLIERS = ["DigitalSplash"]
FIXED_EXTRA_HANDLING = 75  # R75 to be added to all extras
FIXED_REFINEMENT_HANDLING = 50  # R50 to be added to all extras
FIXED_FINISHING_HANDLING = 25  # R25 to be added to all extras


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
    # height -= categories_space[category]["height"]
    # width -= categories_space[category]["width"]
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
    height = float(height)
    width = float(width)
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

def read_google_sheet(folder: str, wb_name: str, sheet_name: str) -> pd.DataFrame:
    wb = service_acc.open(wb_name, folder)
    ws = wb.worksheet(sheet_name)
    values = ws.get_all_values()
    data = pd.DataFrame(values[1:], columns=values[0])
    return data


def get_nth_value(x: str, delim: str, n: int) -> str:
    return x.split(delim)[n]


def calculate_attributes(df: pd.DataFrame)-> pd.DataFrame:
    finishing = get_finishing_costs()
    df = df.reset_index(drop=True)
    print("Calculating Attributes: ", len(df))
    print("Finishing")
    finishing_costs = pd.merge(df[["Supplier", "Quantity", "Finishing", "Total Sheets"]], finishing, "left", left_on=["Supplier", "Finishing"], right_on=["Supplier", "Attribute"])
    finishing_costs["Finishing_costs"] = finishing_costs["Setup-Cost"].fillna(0) +np.where(finishing_costs["value"] > 0,FIXED_FINISHING_HANDLING, 0)  + np.where(finishing_costs["Calculation"] == "PI", finishing_costs["Quantity"] * finishing_costs["value"], finishing_costs["Total Sheets"] *finishing_costs["value"])
    finishing_costs["Finishing_costs"] = np.where(finishing_costs["Finishing"] == "None",0, finishing_costs["Finishing_costs"])
    print("Extra")
    # Extra Costs
    extra_costs = pd.merge(df[["Supplier", "Quantity", "Extra", "Total Sheets"]], finishing, "left", left_on=["Supplier", "Extra"], right_on=["Supplier", "Attribute"])

    # NOTE: Check later which cases that apply to: Drilling, holes, should be applied as minimum handling fees
    extra_costs["Extra_costs"] = extra_costs["Setup-Cost"].fillna(0) + np.where(extra_costs["value"] > 0,FIXED_EXTRA_HANDLING, 0) + np.where(extra_costs["Calculation"] == "PI", extra_costs["Quantity"] * extra_costs["value"], extra_costs["Total Sheets"] *extra_costs["value"])
    extra_costs["Extra_costs"] = np.where(extra_costs["Extra"] == "None", 0, extra_costs["Extra_costs"])
    print("Binding")
    # Binding Costs
    binding_costs = pd.merge(df[["Supplier", "Quantity", "Binding", "Total Sheets"]], finishing, "left", left_on=["Supplier", "Binding"], right_on=["Supplier", "Attribute"])
    binding_costs["Binding_costs"] = binding_costs["Setup-Cost"].fillna(0) + np.where(binding_costs["Calculation"] == "PI", binding_costs["Quantity"] * binding_costs["value"], binding_costs["Total Sheets"] *binding_costs["value"])
    binding_costs["Binding_costs"] = np.where(binding_costs["Binding_costs"] == 0, None, binding_costs["Binding_costs"])
    binding_costs["Binding_costs"] = np.where(binding_costs["Binding"] == "None", 0, binding_costs["Binding_costs"])
    print("Refinement")
    # Refinement Costs
    refinement = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Refinement")
    refinement = pd.melt(refinement, id_vars="Refinement", var_name="Supplier", value_name="Refinement_costs")
    refinement = refinement[refinement["Refinement_costs"]!= "" ]
    refinement["Refinement_costs"] = pd.to_numeric(refinement["Refinement_costs"], errors="coerce")

    df["Finishing_costs"] = finishing_costs["Finishing_costs"]
    df["Binding_costs"] = df["Binding_costs"] + binding_costs["Binding_costs"].fillna(0)
    df["Extra_costs"] = extra_costs["Extra_costs"]
    print(len(df))

    del (finishing_costs)
    del (binding_costs)
    del (extra_costs)

    df = df.reset_index(drop=True)
    df = pd.merge(df, refinement, "left", on=["Supplier", "Refinement"])
    df["Refinement_costs"] = df["Refinement_costs"] * df["SQM"] * df["Total Sheets"]
    df["Refinement_costs"] = np.where(df["Refinement_costs"]> 0, df["Refinement_costs"] + FIXED_REFINEMENT_HANDLING, 0)
    df["Refinement_costs"] = np.where(df["Refinement"] == "None", 0, df["Refinement_costs"])

    df["Refinement Costs"] = df["Refinement_costs"] * ( 1 + df["Refinement Markup"] /100)
    df["Extra Costs"] = df["Extra_costs"] * (1 + df["Option Markup"] /100)
    df["Binding Costs"] = df["Binding_costs"] *(1 + df["Binding Markup"] /100)
    df["Finishing Costs"] = df["Finishing_costs"] *(1 + df["Finishing Markup"] /100)
    df["Total Printing Costs"] = df["Printing and Paper incl Markup"] * (1 + df["Printing Markup"] /100)

    # df["Total Costs"] = df["Total Printing Costs"] + df["Refinement Costs"] + df["Extra Costs"] + df["Binding Costs"] + df["Finishing_costs"]
    # df["Total Costs"] = np.where(df["Total Costs"] < 75, 75, df["Total Costs"])
    # df["Shipping Costs"] = np.where(df["Shipping Costs"] < 100, 100, df["Shipping Costs"]) 
    # df["Total Costs"] = df["Total Costs"] + df["Shipping Costs"]
    # df = df[df["Total Costs"].isna() == False]
    # df = df.sort_values("Total Costs", ascending=True)
    # df = df.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Supplier", "Quantity"])
    # print(len(df))
    # df = df.sort_values("Total Costs", ascending=False)
    # df = df.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Quantity"])
    # df = df.reset_index(drop=True)
    print("Finished Attributes: ", len(df))
    df = df.reset_index(drop=True)
    return df

def get_finishing_costs()-> pd.DataFrame:
    if "finishing" in cached_data.keys():
        return cached_data["finishing"]
    finishing = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Finishing")
    finishing = pd.melt(finishing , id_vars=["Attribute", "Calculation"], var_name="Supplier")
    finishing = finishing [finishing["value"] != ""]
    finishing["Setup-Cost"] = finishing ["value"].str.extract("(.*)\+")
    finishing["Setup-Cost"] = pd.to_numeric(finishing["Setup-Cost"],errors="coerce")
    finishing["Setup-Cost"] = finishing["Setup-Cost"].fillna(0).astype("float32")
    finishing["value"] = finishing["value"].str.replace(".*\+","",regex=True)
    finishing["/1000"] = finishing["value"].str.extract("(/\s?1000)")
    finishing["/1000"] = finishing["value"].str.contains("(/\s?1000)")
    finishing["value"] = finishing["value"].str.replace("(/\s?1000)","",regex=True)
    finishing["value"] = pd.to_numeric(finishing["value"], errors="coerce")
    finishing["value"] = np.where(finishing["/1000"], finishing["value"] / 1000 , finishing["value"])
    finishing["value"] = finishing["value"].astype("float32")
    finishing = finishing[finishing["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    finishing[["Attribute", "Calculation", "Supplier"]] = finishing[["Attribute", "Calculation", "Supplier"]].astype("category")
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
    additional_prices = additional_prices[additional_prices["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    markup = additional_prices[additional_prices["Attribute"].str.contains("Markup")].reset_index(drop=True)
    markup = markup[markup["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    markup = markup[["Supplier", "value"]].rename({"value": "Supplier Markup"},axis=1)
    cached_data["additional"] = additional_prices, markup
    return additional_prices, markup


def get_paper_costs()-> pd.DataFrame:
    if "paper" in cached_data.keys():
        return cached_data["paper"]
    paper_prices = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Paper Price")
    paper_prices = paper_prices[["Grammage", "Sheet Size", "Price incl 5%"]]
    paper_prices = paper_prices.rename({"Grammage": "Paper", "Price incl 5%": "Paper Costs"}, axis=1)
    paper_prices["Paper Costs"] = paper_prices["Paper Costs"].astype(float)
    cached_data["paper"] = paper_prices
    return paper_prices

color_map = {"FC": 4, "B":1}


def get_clicks()-> pd.DataFrame:
    if "clicks" in cached_data.keys():
        return cached_data["clicks"]
    clicks_costs = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Digital Clicks")
    clicks_costs = pd.melt(clicks_costs, "Attribute", var_name="Supplier", value_name="Clicks Cost")
    clicks_costs = clicks_costs[clicks_costs["Clicks Cost"]!= ""]
    clicks_costs["Machine_size"] = clicks_costs["Attribute"].str.extract(r"(A\d)")
    clicks_costs["Workstyle"] = clicks_costs["Attribute"].str.extract(r"\((.*)\)")
    clicks_costs["Clicks Cost"] = clicks_costs["Clicks Cost"].astype(float)
    clicks_costs["Color"] = clicks_costs["Attribute"].str.extract(r"-(.*)_")
    clicks_costs["Front_colour"] = clicks_costs["Color"].map(color_map)
    clicks_costs["Back_colour"] = np.where(clicks_costs["Workstyle"]== "Simplex", 0, clicks_costs["Front_colour"])
    clicks_costs = clicks_costs.drop(["Attribute", "Color"], axis=1)
    clicks_costs = clicks_costs[clicks_costs["Supplier"].isin(REMOVED_SUPPLIERS) == False]
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
    litho_machines = litho_machines[litho_machines["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    litho_machines[["Supplier", "Machine_size"]] = litho_machines[["Supplier", "Machine_size"]].astype("category")
    litho_machines[["Cost", "Plates Costs", "Setup Time", "Sheets / Hour"]] = litho_machines[["Cost", "Plates Costs", "Setup Time", "Sheets / Hour"]].astype('float16')
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
    lf_machines = lf_machines[lf_machines["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    lf_machines[["Supplier", "colors", "Machine"]] = lf_machines[["Supplier", "colors", "Machine"]].astype("category")
    lf_machines["Printing Rate"] = lf_machines["Printing Rate"].astype("float16")
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
    lf_waste[["Supplier", "Paper"]] = lf_waste[["Supplier", "Paper"]].astype("category")
    lf_waste = lf_waste[lf_waste["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    lf_waste["Waste %"] = lf_waste["Waste %"].astype('float16')
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
    lf_cutting = lf_cutting[lf_cutting["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    lf_cutting[["Supplier", "Paper"]] = lf_cutting[["Supplier", "Paper"]].astype("category")
    lf_cutting["LF Cutting"] = lf_cutting["LF Cutting"].astype("float16")
    cached_data["lf_cutting"] = lf_cutting
    return lf_cutting


def get_lf_material() -> pd.DataFrame:
    if "lf_material" in cached_data.keys():
        return cached_data["lf_material"]
    lf_material = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "LF Material")
    lf_material = pd.melt(lf_material, ["Attribute","GSM"], var_name="Supplier")
    lf_material = lf_material[lf_material["value"] != ""]
    lf_material["value"] = pd.to_numeric(lf_material["value"]).astype("float16")
    lf_material["GSM"] = pd.to_numeric(lf_material["GSM"]).astype("float16")
    lf_material = lf_material.rename({"value": "LF Material", "Attribute": "Paper"}, axis=1)
    lf_material = lf_material[lf_material["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    lf_material[["Supplier", "Paper"]] = lf_material[["Supplier", "Paper"]].astype("category")
    cached_data["lf_material"] = lf_material
    return lf_material


def get_lf_extra() -> pd.DataFrame:
    if "lf_extra" in cached_data.keys():
        return cached_data["lf_extra"]
    lf_extra = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "LF Extra")
    lf_extra = pd.melt(lf_extra, "Attribute", var_name="Supplier")
    lf_extra = lf_extra[lf_extra["value"] != ""]
    lf_extra["value"] = pd.to_numeric(lf_extra["value"]).astype("float16")
    lf_extra = lf_extra.rename({"value": "LF Extra", "Attribute": "Extra"}, axis=1)
    lf_extra = lf_extra[lf_extra["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    lf_extra[["Supplier", "Extra"]] = lf_extra[["Supplier", "Extra"]].astype("category")
    cached_data["lf_extra"] = lf_extra
    return lf_extra


def get_lf_refinement() -> pd.DataFrame:
    if "lf_refinement" in cached_data.keys():
        return cached_data["lf_refinement"]
    lf_refinement = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "LF Refinement")
    lf_refinement = pd.melt(lf_refinement, "Refinement", var_name="Supplier")
    lf_refinement = lf_refinement[lf_refinement["value"] != ""]
    lf_refinement["value"] = pd.to_numeric(lf_refinement["value"]).astype("float16")
    lf_refinement = lf_refinement.rename({"value": "LF Refinement"}, axis=1)
    lf_refinement = lf_refinement[lf_refinement["Supplier"].isin(REMOVED_SUPPLIERS) == False]
    lf_refinement[["Supplier", "Refinement"]] = lf_refinement[["Supplier", "Refinement"]].astype("category")
    cached_data["lf_refinement"] = lf_refinement
    return lf_refinement


def get_wiro_pur_binding_costs() -> pd.DataFrame:
    if "wiro" in cached_data.keys():
        return cached_data["wiro"], cached_data["wiro_thickness"], cached_data["wiro_length"], cached_data["hangers"], cached_data["hanger_length"], cached_data["pur"], cached_data["pur_thickness"], cached_data["pur_quantity"]
    binding_prices = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Binding")
    binding_prices = pd.melt(binding_prices, id_vars=["Attribute", "Length", "Setup", "Quantity"], var_name="Thickness")
    binding_prices = binding_prices[binding_prices["value"] != ""]
    binding_prices["Thickness"] = pd.to_numeric(binding_prices["Thickness"]).astype(str)
    binding_prices["Thickness"] = binding_prices["Thickness"].replace("\.0", "", regex=True)
    binding_prices["Length"] = pd.to_numeric(binding_prices["Length"]).astype(str)
    binding_prices["Length"] = binding_prices["Length"].replace("\.0", "", regex=True)
    binding_prices["value"] = pd.to_numeric(binding_prices["value"], errors="coerce")
    binding_prices["Setup"] = pd.to_numeric(binding_prices["Setup"], errors="coerce")
    binding_prices["Quantity"] = pd.to_numeric(binding_prices["Quantity"], errors="coerce")
    wiro_prices = binding_prices[(binding_prices["Attribute"].str.contains("Wiro Binding"))& (binding_prices["Attribute"].str.contains("Hanger") == False) | (binding_prices["Attribute"].str.contains("Spiral"))]
    hangers_prices = binding_prices[binding_prices["Attribute"].str.contains("Hanger")]
    pur_prices = binding_prices[binding_prices["Attribute"].str.contains("PUR")]
    del (binding_prices)
    cached_data["wiro"] = wiro_prices
    cached_data["hangers"] = hangers_prices
    cached_data["pur"] = pur_prices
    wiro_thickness = list(set(wiro_prices["Thickness"]))
    wiro_thickness = [float(thic) for thic in wiro_thickness]
    wiro_length = list(set(wiro_prices["Length"]))
    wiro_length = [float(thic) for thic in wiro_length]
    hanger_length = list(set(hangers_prices["Length"]))
    hanger_length = [float(thic) for thic in hanger_length]
    pur_thickness = list(set(pur_prices["Thickness"]))
    pur_thickness = [float(thic) for thic in pur_thickness]
    pur_quantity = list(set(pur_prices["Quantity"]))
    cached_data["wiro_thickness"] = wiro_thickness
    cached_data["wiro_length"] = wiro_length
    cached_data["hanger_length"] = hanger_length
    cached_data["pur_thickness"] = pur_thickness
    cached_data["pur_quantity"] = pur_quantity
    return wiro_prices, wiro_thickness, wiro_length, hangers_prices, hanger_length, pur_prices, pur_thickness, pur_quantity


def get_litho_utilization()-> pd.DataFrame:
    if "litho_utilization" in cached_data.keys():
        return cached_data["litho_utilization"]
    litho_utilization = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Litho Utilization")
    litho_utilization["Ganging Utilization"] = pd.to_numeric(litho_utilization["Ganging Utilization"], errors="coerce").astype("float16")
    litho_utilization[["Sheet Size", "Paper", "Paper Code"]] = litho_utilization[["Sheet Size", "Paper", "Paper Code"]].astype("category")
    cached_data["litho_utilization"] = litho_utilization
    return litho_utilization


def get_wiro_thickness() -> pd.DataFrame:
    if "wiro_thickness" in cached_data.keys():
        return cached_data["wiro_thickness"]
    wiro_thickness = get_wiro_pur_binding_costs()[1]
    cached_data["wiro_thickness"] = wiro_thickness
    return wiro_thickness


def get_wiro_length() -> pd.DataFrame:
    if "wiro_length" in cached_data.keys():
        return cached_data["wiro_length"]
    wiro_length = get_wiro_pur_binding_costs()[2]
    cached_data["wiro_length"] = wiro_length
    return wiro_length


def get_pur_thickness() -> pd.DataFrame:
    if "pur_thickness" in cached_data.keys():
        return cached_data["pur_thickness"]
    pur_thickness = get_wiro_pur_binding_costs()[6]
    cached_data["pur_thickness"] = pur_thickness
    return pur_thickness


def get_hanger_length() -> pd.DataFrame:
    if "hanger_length" in cached_data.keys():
        return cached_data["hanger_length"]
    hanger_length = get_wiro_pur_binding_costs()[4]
    cached_data["hanger_length"] = hanger_length
    return hanger_length


def get_pur_quantity() -> pd.DataFrame:
    if "pur_quantity" in cached_data.keys():
        return cached_data["pur_quantity"]
    pur_quantity = get_wiro_pur_binding_costs()[7]
    cached_data["pur_quantity"] = pur_quantity
    return pur_quantity


def get_shipping_costs() -> pd.DataFrame:
    if "shipping" in cached_data.keys():
        return cached_data["shipping"]
    shipping = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Shipping")# .iloc[0, :]
    shipping = shipping[shipping["Destination"] == "National"]
    shipping[["Minimum", "Minimum KG", "Kg After"]] = shipping[["Minimum", "Minimum KG", "Kg After"]].astype('float32')
    cached_data["shipping"] = shipping
    return shipping


def get_weights() -> pd.DataFrame:
    if "weights" in cached_data.keys():
        return cached_data["weights"]
    weights = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "GSM")
    weights = weights[weights["GSM"] != ""].reset_index(drop=True)
    weights["GSM"] = pd.to_numeric(weights["GSM"]).astype("float16")
    weights[["Attribute", "Type"]] = weights[["Attribute", "Type"]].astype("category")
    cached_data["weights"] = weights
    return weights


def get_custom() -> pd.DataFrame:
    if "custom" in cached_data.keys():
        return cached_data["custom"]
    custom = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Custom")
    custom["Setup"] = custom["Setup"]
    custom["Unit KG"] = custom["Unit KG"]
    custom["Unit Price"] = custom["Unit Price"]
    custom[["Setup", "Unit Price", "Unit KG"]] = custom[["Setup", "Unit Price", "Unit KG"]].astype("float32")
    cached_data["custom"] = custom
    return custom


if __name__ == "__main__":
    sqm = get_litho_sf_SQM("format_20x28_7_0")
    print(sqm)

    pass
