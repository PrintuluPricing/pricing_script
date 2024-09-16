import pandas as pd
import numpy as np
from helper_pricing import get_lf_cutting, get_lf_double, get_lf_extra, get_lf_mahcines, get_lf_material, get_lf_waste, get_weights, get_shipping_costs


def calculation(df: pd.DataFrame)-> pd.DataFrame:
    lf_printing_rates = get_lf_mahcines()
    lf_printing_rates = df.merge(lf_printing_rates, "left", on="colors")
    # FIXME: Check combinations here!!
    df[["Supplier", "Printing Rate", "Machine"]] = lf_printing_rates[["Supplier", "Printing Rate", "Machine"]]
    lf_waste = get_lf_waste()
    lf_waste = df.merge(lf_waste, "left", on=["Supplier", "Paper"])
    df["Waste %"] = lf_waste["Waste %"].fillna(0)
    lf_double = get_lf_double()
    df["LF Double"] = np.where(df["Paper"].isin(lf_double),2,1)
    lf_cutting = get_lf_cutting()
    lf_cutting = df.merge(lf_cutting, "left", on=["Supplier", "Paper"])
    df["LF Cutting"] = lf_cutting["LF Cutting"].fillna(0) * df["SQM"]
    lf_material = get_lf_material()
    lf_material = df.merge(lf_material, "left", on=["Paper", "Supplier"])
    df["LF Material"] = lf_material["LF Material"]
    df["GSM"] = lf_material["GSM"]
    df["LF Material"] = df["LF Material"] * df["SQM"] * df["LF Double"] * (df["Waste %"] + 1)
    # df = df[df["LF Material"].isna()== False].reset_index(drop=True)
    df["Printing and Paper Costs"] = df["Printing Rate"] + df["LF Cutting"] + df["LF Material"]
    lf_extra = get_lf_extra()
    lf_extra = df.merge(lf_extra, "left", on=["Extra", "Supplier"])
    lf_extra.to_csv("LF Extra.csv", index=False)
    df["LF Extra"] = lf_extra["LF Extra"]
    df["LF Extra"] = df["LF Extra"] * df["Quantity"]
    # df = df[df["LF Extra"].isna()== False].reset_index(drop=True)
    # df["Paper Weight"] = df["GSM"] * df["SQM"] / 1000
    weights = get_weights()
    refinement_weights = weights[weights["Type"] == "Refinement"].reset_index(drop=True)
    refinement_weights = df[["Refinement"]].merge(refinement_weights, "left", left_on="Refinement", right_on="Attribute")
    df["Refinement GSM"] = refinement_weights["GSM"]
    extra_weights = weights[weights["Type"] == "Extra"].reset_index(drop=True)
    extra_weights = df[["Extra"]].merge(extra_weights, "left", left_on="Extra", right_on="Attribute")
    df["Extra GSM"] = extra_weights["GSM"]
    df["Refinement GSM"] = df["Refinement GSM"].fillna(0)
    df["Extra GSM"] = df["Extra GSM"].fillna(0)
    df["GSM"] = df["GSM"] + df["Refinement GSM"] + df["Extra GSM"]
    df["Total Weight"] = df["GSM"] * df["SQM"] / 1000
    shipping_costs = get_shipping_costs()
    df["Remaining"] = np.floor(df["Total Weight"] - shipping_costs["Minimum KG"])
    df["Remaining"] = np.where(df["Remaining"] < 0, 0, df["Remaining"])
    df["Shipping Costs"] = df["Remaining"] * shipping_costs["Kg After"] + shipping_costs["Minimum"]
    df["Printing and Paper Markup"] = df["Printing and Paper Costs"] * (1 + df["Printing Markup"]/100)
    df["LF Extra Markup"] = df["LF Extra"] * ( 1 + df["Option Markup"]/100)
    df["Total Costs"] = df["Printing and Paper Markup"] + df["LF Extra Markup"] + df["Shipping Costs"]

    return df
