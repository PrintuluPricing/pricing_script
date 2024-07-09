import pandas as pd
import numpy as np
import gspread
import re
from helper_pricing import read_google_sheet, cached_data


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

binding_thickness = [1,115,20,12]

def get_closest_thickness(thickness):
    if thickness in binding_thickness:
        return thickness
    binding_thickness_bigger = [qty for qty in binding_thickness if qty > thickness]
    if thickness > max(binding_thickness):
        return max(binding_thickness)
    return sorted(binding_thickness_bigger)[0] if len(binding_thickness_bigger) > 0 else min(binding_thickness)


def calculate_binding(df: pd.DataFrame) -> pd.DataFrame:
    if "wiro" in cached_data.keys():
        binding_prices = cached_data["wiro"]
    # Include dataframe
    # thickness = df["GSM"] * df["PagesNumber"] / 2000 + 4 # Calculate the thickness in mm
    # df["Length (mm)"]
    binding_prices = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Binding")
    binding_prices = pd.melt(binding_prices, id_vars=["Attribute", "Length", "Setup"], var_name="Thickness")
    binding_prices = binding_prices[binding_prices["value"] != ""]
    # binding_prices[["Length", "Setup", "value", "Thickness"]] = pd.to_numeric(binding_prices[["Length", "Setup", "value", "Thickness"]])
    binding_prices["value"] = pd.to_numeric(binding_prices["value"], errors="coerce")
    cached_data["wiro"] = binding_prices
    binding_thickness = list(set(binding_prices["Thickness"]))
    binding_thickness = [float(thic) for thic in binding_thickness]
    print(binding_thickness)


if __name__ == "__main__":
    # calculate_binding(None)
    print(get_closest_thickness(180))
