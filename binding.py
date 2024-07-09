import pandas as pd
import numpy as np
import gspread
import re
from helper_pricing import read_google_sheet


INPUT_PRICES_FOLDER = "1BrbtZ82ygpJ6Yu6m0nWboa2KN-rDe7PT"


key = "sheets_key_new.json"
service_acc = gspread.service_account(key)


# TODO: Wiro Calculation
# Calculate Paper Thickness

# Paper Thickness = gsm * pages Number /2000 + 4 => Paper thickness in mm

# Check which part of the format is the length

# The wiro costs in the old pricing is supposed to be with setup cost of 200

# Old Pricing has setup cost of 200

# Setup Cost with Future Fusion is 350 and not 200


# TODO: Pur Binding Calculation

# Calculate the thickness

# Old Pricing -> Setup Cost 350


def get_closest_length():
    pass


def get_closest_thickness():
    pass


def calculate_binding(df: pd.DataFrame) -> pd.DataFrame:
    thickness = df["GSM"] * df["PagesNumber"] / 2000 + 4 # Calculate the thickness in mm
    # df["Length (mm)"]
    binding_prices = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Binding")
    binding_prices = pd.melt(binding_prices, id_vars=["Attribute", "Length", "Setup"], var_name="Thickness")
    binding_prices = binding_prices[binding_prices["value"] != ""]
    # binding_prices[["Length", "Setup", "value", "Thickness"]] = pd.to_numeric(binding_prices[["Length", "Setup", "value", "Thickness"]])
    binding_prices["value"] = pd.to_numeric(binding_prices["value"], errors="coerce")
    print(binding_prices)


if __name__ == "__main__":
    calculate_binding(None)
