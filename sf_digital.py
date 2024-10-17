import pandas as pd
import numpy as np
from helper_pricing import get_additional, get_clicks, get_weights, get_paper_costs, get_shipping_costs


def calculation(df: pd.DataFrame) -> pd.DataFrame:
    print("SF Digital calculation started   :", len(df))
    df = df.reset_index(drop=True)
    if len(df) == 0:
        return df
    df["Overs"] = np.where(df["Back_colour"] > 0, 4, 2)
    df["Overs"] = df["Overs"].astype("uint8")
    df["Total Sheets"] = df["printing_sheets"] + df["Overs"]
    df["Total Sheets"] = df["Total Sheets"].astype("uint16")
    clicks_costs = get_clicks()
    df = pd.merge(df, clicks_costs, "left", on=["Machine_size", "Workstyle"])
    df[["Machine_size", "Workstyle"]] = df[["Machine_size", "Workstyle"]].astype("category")
    df["Clicks Cost"] = df["Clicks Cost"] * df["Total Sheets"]
    df["Clicks Cost"] = df["Clicks Cost"].astype("float16")
    df = df[df["Clicks Cost"] > 0]
    df["Paper Costs"] = df["Paper Costs"] * df["Total Sheets"]
    df["Paper Costs"] = df["Paper Costs"].astype("float16")
    df["Printing and Paper Costs"] = df["Clicks Cost"] + df["Paper Costs"]
    df["Printing and Paper Costs"] = df["Printing and Paper Costs"].astype("float16")
    additional_prices, markup = get_additional()
    sf_digital_additional = additional_prices[additional_prices["Attribute"].str.contains("SF - Digital")].reset_index(drop=True)
    sf_digital_additional = pd.merge(sf_digital_additional, markup, "left", on="Supplier")
    sf_digital_additional = sf_digital_additional.rename({"value": "Additional"}, axis=1)
    sf_digital_additional = sf_digital_additional.drop("Attribute", axis=1)
    df = pd.merge(df, sf_digital_additional, "left", on=["Supplier", "Machine_size"])
    df["Printing and Paper incl Markup"] = df["Printing and Paper Costs"] * (1 + df["Supplier Markup"] /100 ) + df["Additional"]
    df["Printing and Paper incl Markup"] = df["Printing and Paper incl Markup"].astype("float16")
    df = df[df["Printing and Paper incl Markup"].isna() == False]
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
    df["Refinement GSM"] = df["Refinement GSM"].fillna(0)
    df["Extra GSM"] = df["Extra GSM"].fillna(0)
    df["GSM"] = df["GSM"] + df["Refinement GSM"] + df["Extra GSM"]
    df["Total Weight"] = df["GSM"] * df["SQM"] / 1000

# Shipping Costs

    shipping_costs = get_shipping_costs()
    df["Remaining"] = np.floor(df["Total Weight"] - shipping_costs["Minimum KG"])
    df["Remaining"] = np.where(df["Remaining"] < 0, 0, df["Remaining"])
    df["Shipping Costs"] = df["Remaining"] * shipping_costs["Kg After"] + shipping_costs["Minimum"]


    df = df.sort_values("Printing and Paper incl Markup", ascending=False)
    df = df.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Supplier", "Quantity"])
    df = df.sort_values("Printing and Paper incl Markup", ascending=True)
    df = df.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Quantity"])

    # df["Total Costs"] = df["Printing and Paper incl Markup"]  # FIX: Updated Later
    print("SF Digital calculation ended   :", len(df))
    df = df.reset_index(drop=True)
    return df
