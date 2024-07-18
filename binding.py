import pandas as pd
import gspread
from helper_pricing import get_wiro_pur_binding_costs, get_wiro_thickness, get_wiro_length, get_pur_thickness, get_hanger_length, get_pur_quantity

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
# 1. Create the thickness length for Wiro, length for Hangers and thickness for PUR Binding
# 2. Add Columns to df => pd.apply => Wiro Length, Wiro Thickness, Hangers Length, Hangers Length, PUR THICKNESS
# 3. Merge Pricing with 



# Calculate the thickness

# Old Pricing -> Setup Cost 350


def get_closest_length():
    pass

def get_closest_thickness(thickness):
    binding_thickness = get_wiro_thickness()
    if thickness in binding_thickness:
        return thickness
    binding_thickness_bigger = [qty for qty in binding_thickness if qty > thickness]
    if thickness > max(binding_thickness):
        return max(binding_thickness)
    return sorted(binding_thickness_bigger)[0] if len(binding_thickness_bigger) > 0 else min(binding_thickness)

def get_closest_length(length):
    binding_length = get_wiro_length()
    if length in binding_length:
        return length
    binding_length_bigger = [qty for qty in binding_length if qty > length]
    if length > max(binding_length):
        return max(binding_length)
    return sorted(binding_length_bigger)[0] if len(binding_length_bigger) > 0 else min(binding_length)


def get_closest_quantities(quantity):
    pur_quantity = get_pur_quantity()
    if quantity in pur_quantity:
        return quantity
    pur_quantity_bigger = [qty for qty in binding_length if qty > length]
    if quantity > max(pur_quantity):
        return max(pur_quantity)
    return sorted(pur_quantity_bigger)[0] if len(pur_quantity_bigger) > 0 else min(pur_quantity)



def calculate_wiro_binding(df: pd.DataFrame) -> pd.DataFrame:
    df["Thickness"] = df["GSM"].astype(int) * df["PagesNumber"].astype(int) / 2000 + 4
    df["Thickness"] = df["Thickness"].apply(get_closest_thickness).astype(str).str.replace("\.0","")
    df["Thickness"] = df["Thickness"].str.replace("\.0", "", regex=True)
    df["Length"] = df["Length"].apply(get_closest_length).astype(str)
    df["Length"] = df["Length"].replace("\.0", "", regex=True)
    wiro_prices = get_wiro_pur_binding_costs()[0]
    # FIX: Check the filter later based on the binding attribute name (Calendar Hanger, Pur, Wiro)
    wiro_prices = wiro_prices[wiro_prices["Attribute"] == "Wiro"]
    wiro_costs = pd.merge(df, wiro_prices, "left", on=["Thickness", "Length"])
    df["Wiro Costs"] = wiro_costs["value"] * df["Quantity"] + wiro_costs["Setup"]
    return df


def calculate_hanger_binding(df: pd.DataFrame) -> pd.DataFrame:
    df["Thickness"] = df["GSM"].astype(int) * df["PagesNumber"].astype(int) / 2000 + 4
    df["Thickness"] = df["Thickness"].apply(get_closest_thickness).astype(str).str.replace("\.0","")
    df["Thickness"] = df["Thickness"].str.replace("\.0", "", regex=True)
    df["Length"] = df["Length"].apply(get_closest_length).astype(str)
    df["Length"] = df["Length"].replace("\.0", "", regex=True)
    wiro_prices = get_wiro_pur_binding_costs()[0]
    # FIX: Check the filter later based on the binding attribute name (Calendar Hanger, Pur, Wiro)
    wiro_prices = wiro_prices[wiro_prices["Attribute"] == "Wiro"]
    wiro_costs = pd.merge(df, wiro_prices, "left", on=["Thickness", "Length"])
    df["Wiro Costs"] = wiro_costs["value"] * wiro_costs["Quantity"] + wiro_costs["Setup"]
    return df


def calculate_pur_binding(df: pd.DataFrame) -> pd.DataFrame:
    df["Thickness"] = df["GSM"].astype(int) * df["PagesNumber"].astype(int) / 2000 + 4
    df["Thickness"] = df["Thickness"].apply(get_closest_thickness).astype(str).str.replace("\.0","")
    df["Thickness"] = df["Thickness"].str.replace("\.0", "", regex=True)
    df["Length"] = df["Length"].apply(get_closest_length).astype(str)
    df["Length"] = df["Length"].replace("\.0", "", regex=True)
    pur = get_wiro_pur_binding_costs()[0]
    wiro_prices = wiro_prices[wiro_prices["Attribute"] == "Wiro"]
    wiro_costs = pd.merge(df, wiro_prices, "left", on=["Thickness", "Length"])
    df["Wiro Costs"] = wiro_costs["value"] * df["Quantity"] + wiro_costs["Setup"]
    return df


if __name__ == "__main__":
    pass
