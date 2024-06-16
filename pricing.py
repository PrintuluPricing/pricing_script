import pandas as pd
# import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe
import glob
import sys
import re


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


# Creating DataFrame

data = pd.read_csv(file_test)
categories = list(set(list(data["Category"])))

litho_data = data[data["Category"] == "Litho"]
sf_digital_data = data[data["Category"] == "SF Digital"]
lf_digital_data = data[data["Category"] == "LF Digital"]


placements = {}


def get_placements(format, category, size):
    x, y = re.findall(r"(\d*\.?\d+)\s?x\s?(\d*\.?\d+)", format)[0]
    x = float(x) + BLEED
    y = float(y) + BLEED
    # height, width = re.findall(r"(\d*\.?\d+)\s?x\s?(\d*\.?\d+)",size)[0]
    # height = np.float_(height)
    # width = np.float_(width)
    # placements1 = int(height/x * width / y)
    # placements2 = int(height/y * width / x)
    sizes = categories_sizes[category]
    for size in sizes:
        height, width = get_size_dimensions(size)
        placements1 = int(height/x * width / y)
        placements2 = int(height/y * width / x)
        placement = max(placements1,placements2)
        print(size, placement)
        placements[format] = {size:placement}

def get_size_dimensions(size: str)-> (float, float):
    height, width = re.findall(r"(\d*\.?\d+)\s?x\s?(\d*\.?\d+)",size)[0]
    height = float(height)
    width = float(width)
    return height, width


get_placements("33.6 x 45.5", "Litho", "45.5 x 64")
get_placements("10.5x 6.7 cm", "Litho", "45.5 x 64")
get_placements("10x 6", "Litho", "45.5 x 64")

print(placements)

