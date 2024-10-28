import pandas as pd
import numpy as np
from helper_pricing import get_lf_cutting, get_lf_double, get_lf_extra, get_lf_mahcines, get_lf_material, get_lf_waste, get_weights, get_shipping_costs, get_lf_SQM, get_lf_refinement
from shipping import calculate_shipping

SHIPPING_MARKUP = 35

def calculation(df: pd.DataFrame)-> pd.DataFrame:
    df = df.reset_index(drop=True)
    lf_printing_rates = get_lf_mahcines()[["Supplier", "Machine", "colors", "Printing Rate"]]
    df = df.merge(lf_printing_rates, "left", on="colors")
    # df[["Supplier", "Printing Rate", "Machine"]] = lf_printing_rates[["Supplier", "Printing Rate", "Machine"]]
    df["SQM"] = df["format"].apply(get_lf_SQM).astype('float32')
    df["SQM"] = df["Quantity"]/ df["SQM"]  # FIX: Check the integer ouptut
    lf_waste = get_lf_waste()
    lf_waste = df.merge(lf_waste, "left", on=["Supplier", "Paper"])
    df["Waste %"] = lf_waste["Waste %"].fillna(0)
    del lf_waste
    lf_double = get_lf_double()
    df["LF Double"] = np.where(df["Paper"].isin(lf_double),2,1)
    # del lf_double
    df["Printing Rate"] = df["Printing Rate"] * df["SQM"] * df["LF Double"]
    lf_cutting = get_lf_cutting()
    lf_cutting = df.merge(lf_cutting, "left", on=["Supplier", "Paper"])
    df["LF Cutting"] = lf_cutting["LF Cutting"]  # .fillna(0) * df["SQM"]
    del lf_cutting
    df["LF Cutting"] = df["LF Cutting"].fillna(0) * df["SQM"]
    lf_material = get_lf_material()
    lf_material = df.merge(lf_material, "left", on=["Paper", "Supplier"])
    df["LF Material"] = lf_material["LF Material"]
    df["GSM"] = lf_material["GSM"]
    del lf_material
    df["LF Material"] = df["LF Material"] * df["SQM"] * df["LF Double"] * (df["Waste %"] + 1)
    df["LF Material"] = df["LF Material"] * df["LF Double"]
    df["Printing and Paper Costs"] = df["Printing Rate"] + df["LF Cutting"] + df["LF Material"]
    lf_extra = get_lf_extra()
    lf_extra = df.merge(lf_extra, "left", on=["Extra", "Supplier"])
    # lf_extra.to_csv("LF Extra.csv", index=False)
    df["LF Extra"] = lf_extra["LF Extra"]
    df["LF Extra"] = np.where(df["Extra"] == "None", 0, df["LF Extra"])
    df["LF Extra"] = df["LF Extra"] * df["Quantity"]

    lf_refinement = get_lf_refinement()
    lf_refinement = df.merge(lf_refinement, "left", on=["Refinement", "Supplier"])
    # lf_extra.to_csv("LF Extra.csv", index=False)
    df["LF Refinement"] = lf_refinement["LF Refinement"]
    df["LF Refinement"] = np.where(df["Refinement"] == "None", 0, df["LF Refinement"])
    df["LF Refinement"] = df["LF Refinement"] * df["SQM"]
    # TODO: Calculate Refinement

# Weight Calculation

    weights = get_weights()
    refinement_weights = weights[weights["Type"] == "Refinement"]  # .reset_index(drop=True)
    refiement_weights = df[["Refinement"]].merge(refinement_weights, "left", left_on="Refinement", right_on="Attribute")
    df["Refinement GSM"] = refiement_weights["GSM"]
    extra_weights = weights[weights["Type"] == "Extra"]  # .reset_index(drop=True)
    extra_weights = df[["Extra"]].merge(extra_weights, "left", left_on="Extra", right_on="Attribute")
    df["Extra GSM"] = extra_weights["GSM"]
    df["Refinement GSM"] = df["Refinement GSM"].fillna(0)
    df["Extra GSM"] = df["Extra GSM"].fillna(0)
    df["GSM"] = df["GSM"].fillna(0) + df["Refinement GSM"] + df["Extra GSM"]
    df["GSM"] = df["GSM"].astype("float32")
    df["Total Weight"] = df["GSM"] * df["SQM"] / 1000
# Shipping Costs

    df = calculate_shipping(df)

    df["Printing and Paper Markup"] = df["Printing and Paper Costs"] * (1 + df["Printing Markup"]/100)
    df["LF Extra Markup"] = df["LF Extra"] * ( 1 + df["Option Markup"]/100)
    df["LF Refinement Markup"] = df["LF Refinement"] * ( 1 + df["Refinement Markup"]/100)
    df["Total Costs"] = df["Printing and Paper Markup"] + df["LF Extra Markup"] + df["Refinement Markup"]
    df["Total Costs"] = np.where(df["Total Costs"] < 75, 75, df["Total Costs"])
    df["Shipping Costs"] = np.where(df["Shipping Costs"] < 100, 100, df["Shipping Costs"]) 
    df["Total Costs"] = df["Total Costs"] + df["Shipping Costs"]

    df = df.reset_index(drop=True)
    return df
