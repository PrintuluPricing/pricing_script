import pandas as pd
import numpy as np
from helper_pricing_mongo import get_clicks, get_weights, calculate_attributes, get_config
from shipping import calculate_shipping
from binding import calculate_binding

config = get_config()

SHIPPING_MARKUP = 35
SHIPPING_MARKUP = config['shipping_markup']
BINDING_NAMES = ["Wiro Binding - Black","Wiro Binding - Silver","Wiro Binding - White","Spiral Binding - Black","Spiral Binding - Silver","Spiral Binding - White","PUR Binding","A2 Wiro Binding - Black with Hanger","A2 Wiro Binding - Silver with Hanger","A2 Wiro Binding - White with Hanger","A3 Wiro Binding - Black with Hanger","A3 Wiro Binding - Silver with Hanger","A3 Wiro Binding - White with Hanger","A4 Wiro Binding - Black with Hanger","A4 Wiro Binding - Silver with Hanger","A4 Wiro Binding - White with Hanger"]

def calculation(df: pd.DataFrame) -> pd.DataFrame:
    print("SF Digital calculation started   :", len(df))
    df = df.reset_index(drop=True)
    print(df.columns)
    if len(df) == 0:
        return df
    bindings = df["Binding"].isin(BINDING_NAMES)
    df["Overs"] = np.where(df["back_colour"] > 0, 4, 2)
    df["Overs"] = df["Overs"].astype("uint8")
    df["Total Sheets"] = df["printing_sheets"] + df["Overs"]
    df["Total Sheets"] = df["Total Sheets"].astype("uint16")
    clicks_costs = get_clicks().drop("colour", axis=1)
    df = pd.merge(df, clicks_costs, "left", on=["machine", "Workstyle", "front_colour", "back_colour"])
    df[["machine", "Workstyle"]] = df[["machine", "Workstyle"]].astype("category")
    df["clicks_cost"] = df["clicks_cost"] * df["Total Sheets"]
    df["clicks_cost"] = df["clicks_cost"].astype("float32")

    df = df[df["clicks_cost"] > 0]
    df["Paper Costs"] = df["Paper Costs"] * df["Total Sheets"]
    df["Paper Costs"] = df["Paper Costs"].astype("float32")
    df["Printing and Paper Costs"] = np.where(df["colour"] == "colour_00", df["Paper Costs"],df["clicks_cost"] + df["Paper Costs"])
    df["Printing and Paper Costs"] = df["Printing and Paper Costs"].astype("float32")

    df["Printing and Paper incl Markup"] = df["Printing and Paper Costs"] * (1 + df["markup_percentage"] /100 ) + df["fixed_price"]
    df["Printing and Paper incl Markup"] = df["Printing and Paper incl Markup"].astype("float32")
    df["Printing and Paper incl Markup"] = np.where(df["colour"] == "colour_00", 0, df["Printing and Paper incl Markup"])
    df = df[df["Printing and Paper incl Markup"].isna() == False]


# NOTE: Cheapest size Selection
    cheapest = df[["idx", "sheet_size", "Printing and Paper incl Markup"]].groupby(["idx", "sheet_size"]).min("Printing and Paper incl Markup")
    cheapest = cheapest.reset_index()
    cheapest = cheapest.sort_values("Printing and Paper incl Markup", ascending=True).drop_duplicates("idx")
    cheapest = cheapest[["idx", "sheet_size"]]
    df = df.merge(cheapest,"inner",on=["idx","sheet_size"])
    del cheapest


# Weight Calculation

    weights = get_weights()
    refinement_weights = weights[weights["Type"] == "Refinement"]  # .reset_index(drop=True)
    refinement_weights = df[["Refinement"]].merge(refinement_weights, "left", left_on="Refinement", right_on="Attribute")
    df["Refinement GSM"] = refinement_weights["GSM"]
    del refinement_weights
    extra_weights = weights[weights["Type"] == "Extra"]  # .reset_index(drop=True)
    extra_weights = df[["Extra"]].merge(extra_weights, "left", left_on="Extra", right_on="Attribute")
    df["Extra GSM"] = extra_weights["GSM"]
    del extra_weights
    df["Refinement GSM"] = df["Refinement GSM"].fillna(0) * df["Total Sheets"]
    df["Extra GSM"] = df["Extra GSM"].fillna(0) * df["Quantity"]
    df["GSM"] = df["GSM"] * df["Total Sheets"] + df["Refinement GSM"] + df["Extra GSM"]
    df["Total Weight"] = df["GSM"] * df["SQM"] / 1000

    df = calculate_shipping(df)
    if np.sum(bindings) > 0:
        df = calculate_binding(df)
    else:
        df["Binding_costs"] = 0
    df = calculate_attributes(df)

    df = df.sort_values("Printing and Paper incl Markup", ascending=True)
    # FIX: include sheet size and category
    df = df.drop_duplicates(["Product Code", "paper", "format", "pages", "colour", "binding", "refinement", "finishing", "extra", "supplier", "Quantity"])
    df = df.reset_index(drop=True)

    df["Total Costs"] = df["Total Printing Costs"] + df["Refinement Costs"] + df["Extra Costs"] + df["Binding Costs"] + df["Finishing Costs"]
    df["Total Costs"] = np.where(df["Total Costs"] < 75, 75, df["Total Costs"])
    df["Shipping Costs"] = np.where(df["Shipping Costs"] < 100, 100, df["Shipping Costs"]) 
    df["Total Costs"] = df["Total Costs"] + df["Shipping Costs"]
    df = df[df["Total Costs"].isna() == False]
    df = df.sort_values("Total Costs", ascending=True)
    df = df.drop_duplicates(["Product Code", "paper", "format", "pages", "colour", "binding", "refinement", "finishing", "extra", "supplier", "Quantity"])
    df = df.reset_index(drop=True)
    print("SF Digital calculation ended   :", len(df))

    return df
