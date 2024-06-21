import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe
import glob
import sys
import re
import warnings

warnings.simplefilter(action="ignore")

# Helper Functions
# PERF: need to update the function for caching
def get_placements1(format, category):
    x, y = get_dimensions(format)
    x = float(x) + BLEED
    y = float(y) + BLEED
    sizes = categories_sizes[category]
    for size in sizes:
        height, width = get_dimensions(size)
        placements1 = int(height/x * width / y)
        placements2 = int(height/y * width / x)
        placement = max(placements1, placements2)
        print(size, placement)
        placements[format] = {size: placement}


def get_placements(format, size):
    x, y = get_dimensions(format)
    x = float(x) + BLEED
    y = float(y) + BLEED
    height, width = get_dimensions(size)
    placements1 = int(height/x * width / y)
    placements2 = int(height/y * width / x)
    placement = max(placements1, placements2)
    placements[format] = {size: placement}
    return placement


def get_dimensions(size: str) -> (float, float):
    size = size.replace("_", ".")
    height, width = re.findall(r"(\d*\.?\d+)\s?x\s?(\d*\.?\d+)",size)[0]
    height = float(height)
    width = float(width)
    return height, width


def get_SQM(format: str) -> float:
    height, width = get_dimensions(format)
    return height * width / 10_000


def read_google_sheet(folder: str, wb_name: str, sheet_name: str):
    wb = service_acc.open(wb_name, folder)
    ws = wb.worksheet(sheet_name)
    values = ws.get_all_values()
    data = pd.DataFrame(values[1:], columns=values[0])
    return data


def get_nth_value(x: str, delim: str, n: int)-> str:
    return x.split(delim)[n]



pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)

# Loading Data
args = sys.argv

files = glob.glob("./*tp*combinations.csv")
file_test = files[0]

key = "sheets_key_new.json"
service_acc = gspread.service_account(key)
# NOTE: Variables
categories_sizes = {
    "Litho": ['45.5 x 64', '51 x 71', '64 x 91.5', '71 x 102'],
    "SF Digital": ['45.5 x 64', '32 x 45.5', '32 x 50', '32 x 64', '32 x 71', '32 x 91.5'],
    "LF Digital": ["100x100"],
}

categories_space = {
    "Litho": {"width": 15, "height": 5},
    "SF Digital": {"width": 1, "height": 1},
    "LF Digital": {"width": 5, "height": 5},
}


machine_sizes = {
    '45.5 x 64': "A2",
    '51 x 71': "A2",
    '64 x 91.5': "A1",
    '71 x 102': "A1",
    '32 x 45.5': "A3",
    '32 x 50': "A3",
    '32 x 64': "A3",
    '32 x 71': "A3",
    '32 x 91.5': "A3",
        }


BLEED = 3
INPUT_PRICES_FOLDER = "1BrbtZ82ygpJ6Yu6m0nWboa2KN-rDe7PT"

placements = {}

# Creating DataFrame

data = pd.read_csv(file_test, keep_default_na=False)
categories = list(set(list(data["Category"])))

# Adding basic calculations
# Calculating pages number, SQM
data["PagesNumber"] = data["Sheets"].str.extract(r"(\d+)").astype(int)
data["height_width"] = data["Format"].apply(get_dimensions)
data["SQM"] = data["Format"].apply(get_SQM)

# FIXME: Only to test remove later
data["Paper"] = "100gsm Gloss"

# Splitting by category
litho_sf_digital_data = data[(data["Category"] == "Litho") | (data["Category"]== "SF Digital")]
lf_digital_data = data[data["Category"] == "LF Digital"]


# Common Calculations for Litho and SF Digital



litho_sf_digital_data["Sheet_size"] = ";".join(categories_sizes["Litho"] + categories_sizes["SF Digital"])
litho_sf_digital_data["Sheet_size"] = litho_sf_digital_data["Sheet_size"].str.split(";")
litho_sf_digital_data = litho_sf_digital_data.explode("Sheet_size")
litho_sf_digital_data["Machine_size"] = litho_sf_digital_data["Sheet_size"].map(machine_sizes)

# Litho Calculations
# NOTE: Check whether to select sheetwise vs other workstyle and which to take by default
litho_sf_digital_data["Workstyle"] = np.where(litho_sf_digital_data["Colour_code"].str[-1] == "0","Simplex","Sheetwise")
litho_sf_digital_data["Front_colour"] = litho_sf_digital_data["Colour_code"].str.extract(r"colour_(\d)\d").astype(int)
litho_sf_digital_data["Back_colour"] = litho_sf_digital_data["Colour_code"].str[-1].astype(int)

# Calculating Placements
litho_sf_digital_data["Placements"] = litho_sf_digital_data.apply(lambda x: get_placements(x["Format"], x["Sheet_size"]),axis=1)
litho_sf_digital_data = litho_sf_digital_data[litho_sf_digital_data["Placements"] > 0]
litho_sf_digital_data["printing_sheets"] = np.ceil(litho_sf_digital_data["Quantity"] * litho_sf_digital_data["PagesNumber"] / litho_sf_digital_data[f"Placements"]).astype(int)

# Calculate Paper Price per Sheet
paper_prices = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Paper Price")
paper_prices = paper_prices[["Grammage", "Sheet_size", "Price incl 5%"]]
paper_prices = paper_prices.rename({"Grammage": "Paper", "Price incl 5%": "Paper Costs"}, axis=1)
paper_prices["Paper Costs"] = paper_prices["Paper Costs"].astype(float)

litho_sf_digital_data = pd.merge(litho_sf_digital_data, paper_prices, "left", on=["Paper", "Sheet_size"])

# Markup Additional Fixed Prices Main
additional_prices = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Fixed Price")
additional_prices = pd.melt(additional_prices, var_name="Supplier", id_vars="Attribute")
additional_prices = additional_prices[additional_prices["value"] != ""]
additional_prices["value"] = additional_prices["value"].astype(float)
additional_prices["Machine_size"] = additional_prices["Attribute"].str.extract(r"(A\d)")
markup = additional_prices[additional_prices["Attribute"].str.contains("Markup")].reset_index(drop=True)
markup = markup[["Supplier", "value"]].rename({"value": "Supplier Markup"},axis=1)

# Split Litho and SF Digital
litho_data = litho_sf_digital_data[litho_sf_digital_data["Category"] == "Litho"]
sf_digital_data = litho_sf_digital_data[litho_sf_digital_data["Category"] == "SF Digital"]

litho_data["Plates"] = np.where(litho_data["Workstyle"].isin(["Simplex", "Sheetwise"]), litho_data["Front_colour"] + litho_data["Back_colour"], (litho_data["Front_colour"]+litho_data["Back_colour"])/2)
litho_data["Overs"] = litho_data["Plates"] * 50
litho_data["Total Sheets"] = litho_data["printing_sheets"] + litho_data["Overs"]
# Machine Prices

litho_machines = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Machine Costs")
litho_machines = pd.melt(litho_machines, ["Attribute", "Category"],var_name="Supplier")
litho_machines = litho_machines[litho_machines["value"] != ""]
litho_machines["value"] = litho_machines["value"].astype(float)
litho_machines["Machine_size"] = litho_machines["Attribute"].str.extract(r"(A\d)")
litho_machines = pd.pivot(litho_machines,columns="Category",values="value",index=["Machine_size","Supplier"]).reset_index()
litho_data = pd.merge(litho_data,litho_machines,"left",on="Machine_size")
litho_data = litho_data[litho_data["Plates Costs"].isna() == False]
litho_data["Setup Cost"] = litho_data["Setup Time"] * litho_data["Plates"] / 60 * litho_data["Cost"] + litho_data["Total Sheets"] / litho_data["Sheets / Hour"] * litho_data["Cost"]
litho_data["Plates Cost"] = litho_data["Plates"] * litho_data["Plates Costs"]
litho_data["Litho Costs"] = litho_data["Setup Cost"] + litho_data["Plates Cost"]
litho_data["Paper Costs"] = litho_data["Paper Costs"] * litho_data["Total Sheets"]
litho_data["Printing and Paper Costs"] = litho_data["Litho Costs"] + litho_data["Paper Costs"]

# Additional and markup
# TODO: Check where to move based on the function

litho_additional = additional_prices[additional_prices["Attribute"].str.contains("Litho")].reset_index(drop=True)
litho_additional = pd.merge(litho_additional, markup, "left", on="Supplier")
litho_additional = litho_additional.rename({"value": "Additional"}, axis=1)

litho_data = pd.merge(litho_data, litho_additional, "left", on=["Supplier", "Machine_size"])
litho_data["Printing and Paper incl Markup"] = litho_data["Printing and Paper Costs"] * (1 + litho_data["Supplier Markup"] /100 ) + litho_data["Additional"]


# Finishing Costs

finishing_costs = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Finishing")
finishing_costs = pd.melt(finishing_costs, id_vars=["Attribute", "Calculation"], var_name="Supplier")
finishing_costs = finishing_costs[finishing_costs["value"] != ""]
finishing_costs["Setup-Cost"] = finishing_costs["value"].str.extract("(.*)\+")
finishing_costs["Setup-Cost"] = pd.to_numeric(finishing_costs["Setup-Cost"],errors="coerce")
finishing_costs["value"] = finishing_costs["value"].str.replace(".*\+","",regex=True)
print(finishing_costs["value"])
exit()

# Extra Costs

# Binding Costs


# Refinement Costs










# SF Digital Calculation
sf_digital_data["Overs"] = np.where(sf_digital_data["Back_colour"] > 0 , 4 , 2 )
sf_digital_data["Total Sheets"] = sf_digital_data["printing_sheets"] + sf_digital_data["Overs"]

clicks_costs = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Digital Clicks")
clicks_costs = pd.melt(clicks_costs, "Attribute", var_name="Supplier", value_name="Clicks Cost")
clicks_costs = clicks_costs[clicks_costs["Clicks Cost"]!= ""]
clicks_costs["Machine_size"] = clicks_costs["Attribute"].str.extract(r"(A\d)")
clicks_costs["Workstyle"] = clicks_costs["Attribute"].str.extract(r"\((.*)\)")
clicks_costs["Clicks Cost"] = clicks_costs["Clicks Cost"].astype(float)
clicks_costs = clicks_costs.drop("Attribute", axis=1)

sf_digital_data = pd.merge(sf_digital_data, clicks_costs, "left", on=["Machine_size", "Workstyle"])
sf_digital_data["Clicks Cost"] = sf_digital_data["Clicks Cost"] * sf_digital_data["Total Sheets"]
sf_digital_data = sf_digital_data[sf_digital_data["Clicks Cost"] > 0]
sf_digital_data["Paper Costs"] = sf_digital_data["Paper Costs"] * sf_digital_data["Total Sheets"]
sf_digital_data["Printing and Paper Costs"] = sf_digital_data["Clicks Cost"] + sf_digital_data["Paper Costs"]

# Additioanl Prices
sf_digital_additional = additional_prices[additional_prices["Attribute"].str.contains("SF - Digital")].reset_index(drop=True)
sf_digital_additional = pd.merge(sf_digital_additional, markup, "left", on="Supplier")
sf_digital_additional = sf_digital_additional.rename({"value": "Additional"}, axis=1)

sf_digital_data = pd.merge(sf_digital_data, sf_digital_additional, "left", on=["Supplier", "Machine_size"])
sf_digital_data["Printing and Paper incl Markup"] = sf_digital_data["Printing and Paper Costs"] * (1 + sf_digital_data["Supplier Markup"] /100 ) + sf_digital_data["Additional"]


litho_data.to_csv("test_litho.csv",index=False)
sf_digital_data.to_csv("test_sf_digital.csv", index=False)
