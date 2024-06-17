import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe
import glob
import sys
import re
import warnings

warnings.simplefilter(action="ignore")


pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)

# Loading Data
args = sys.argv

files = glob.glob("./*tp*combinations.csv")
file_test = files[0]

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

placements = {}

# Helper Functions
# FIX: need to update the function for caching
def get_placements1(format, category):
    x, y = get_dimensions(format)
    x = float(x) + BLEED
    y = float(y) + BLEED
    sizes = categories_sizes[category]
    for size in sizes:
        height, width = get_dimensions(size)
        placements1 = int(height/x * width / y)
        placements2 = int(height/y * width / x)
        placement = max(placements1,placements2)
        print(size, placement)
        placements[format] = {size:placement}


def get_placements(format, size):
    x, y = get_dimensions(format)
    x = float(x) + BLEED
    y = float(y) + BLEED
    height, width = get_dimensions(size)
    placements1 = int(height/x * width / y)
    placements2 = int(height/y * width / x)
    placement = max(placements1,placements2)
    placements[format] = {size: placement}
    return placement


def get_dimensions(size: str)-> (float, float):
    size = size.replace("_",".")
    height, width = re.findall(r"(\d*\.?\d+)\s?x\s?(\d*\.?\d+)",size)[0]
    height = float(height)
    width = float(width)
    return height, width

def get_SQM(format: str)-> float:
    height, width = get_dimensions(format)
    return height * width / 10_000


# Creating DataFrame

data = pd.read_csv(file_test, keep_default_na=False)
categories = list(set(list(data["Category"])))

# Adding basic calculations
# Calculating pages number, SQM
data["PagesNumber"] = data["Sheets"].str.extract(r"(\d+)").astype(int)
data["height_width"] = data["Format"].apply(get_dimensions)
data["SQM"] = data["Format"].apply(get_SQM)


# Splitting by category
litho_data = data[data["Category"] == "Litho"]
sf_digital_data = data[data["Category"] == "SF Digital"]
lf_digital_data = data[data["Category"] == "LF Digital"]

litho_data["Sheet_size"] = ";".join(categories_sizes["Litho"])
litho_data["Sheet_size"] = litho_data["Sheet_size"].str.split(";")
litho_data = litho_data.explode("Sheet_size")
litho_data["Machine_size"] = litho_data["Sheet_size"].map(machine_sizes)

# Litho Calculations
# NOTE: Check whether to select sheetwise vs other workstyle and which to take by default
litho_data["Workstyle"] = np.where(litho_data["Colour_code"].str[-1] == "0","Simplex","Sheetwise")
litho_data["Front_colour"] = litho_data["Colour_code"].str.extract(r"colour_(\d)\d").astype(int)
litho_data["Back_colour"] = litho_data["Colour_code"].str[-1].astype(int)

# Calculating Placements
litho_data["Placements"] = litho_data.apply(lambda x: get_placements(x["Format"], x["Sheet_size"]),axis=1)
litho_data["printing_sheets"] = np.ceil(litho_data["Quantity"] * litho_data["PagesNumber"] / litho_data[f"Placements"]).astype(int)

# TODO: Calculate the plates / overs
litho_data["Plates"] = np.where(litho_data["Workstyle"].isin(["Simplex", "Sheetwise"]), litho_data["Front_colour"] +
                                litho_data["Back_colour"], (litho_data["Front_colour"]+litho_data["Back_colour"])/2)
litho_data["Overs"] = litho_data["Plates"] * 50





print(litho_data)

litho_data.to_csv("test_litho.csv",index=False)
