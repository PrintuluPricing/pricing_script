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
    "Litho": ['45.5 x 64', '51 x 71', '64 x 91.5', '45.5 x 64', '71 x 102'],
    "SF Digital": ['32 x 45.5', '32 x 50', '32 x 64', '32 x 71', '32 x 91.5'],
    "LF Digital": ["100x100"],
}

categories_space = {
    "Litho": {"width": 15, "height": 5},
    "SF Digital": {"width": 1, "height": 1},
    "LF Digital": {"width": 5, "height": 5},
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
    height, width = re.findall(r"(\d*\.?\d+)\s?x\s?(\d*\.?\d+)",size)[0]
    height = float(height)
    width = float(width)
    return height, width

def get_SQM(format: str)-> float:
    height, width = get_dimensions(format)
    return height * width / 10_000


# Creating DataFrame

data = pd.read_csv(file_test, keep_default_na=True)
categories = list(set(list(data["Category"])))

# Adding basic calculations
# Calculating pages number, SQM
data["PagesNumber"] = data["Sheets"].str.extract(r"(\d+)").astype(int)
data["SQM"] = data["Format"].apply(get_SQM)


# Splitting by category
litho_data = data[data["Category"] == "Litho"]
sf_digital_data = data[data["Category"] == "SF Digital"]
lf_digital_data = data[data["Category"] == "LF Digital"]

# Litho Calculations
litho_data["Workstyle"] = litho_data["Colour"]
print(litho_data["Workstyle"])

for size in categories_sizes["Litho"]:
    litho_data[f"Placements_{size}"] = litho_data["Format"].apply(lambda x: get_placements(x, size))
    litho_data[f"printing_sheets_{size}"] = np.ceil(litho_data["Quantity"] * litho_data["PagesNumber"] / litho_data[f"Placements_{size}"]).astype(int)

    # TODO: Calculate the plates / overs


# litho_data.to_csv("test_litho.csv",index=False)
