import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe
import glob
import sys
import warnings
from helper_pricing import get_finishing_costs, get_dimensions, get_SQM, calculate_attributes
import litho_sf_digital
import litho
import sf_digital

warnings.simplefilter(action="ignore")

pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)

# Loading Data
args = sys.argv

files = glob.glob("./*tp*combinations.csv")
file_test = files[0]



finishing = get_finishing_costs()

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

litho_sf_digital_data = litho_sf_digital.calculation(litho_sf_digital_data)

# Split Litho and SF Digital
litho_data = litho_sf_digital_data[litho_sf_digital_data["Category"] == "Litho"]
sf_digital_data = litho_sf_digital_data[litho_sf_digital_data["Category"] == "SF Digital"]
litho_data = litho.calculation(litho_data)
litho_data = calculate_attributes(litho_data, finishing)

# SF Digital Calculation
sf_digital_data = sf_digital.calculation(sf_digital_data)
sf_digital_data = calculate_attributes(sf_digital_data, finishing)

litho_data.to_csv("test_litho.csv",index=False)
sf_digital_data.to_csv("test_sf_digital.csv", index=False)
