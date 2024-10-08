import pandas as pd
import numpy as np
from helper_pricing import get_additional, get_litho_machines, get_litho_utilization, get_weights, get_shipping_costs


def calculation(df: pd.DataFrame)-> pd.DataFrame:
    # FIXME: Update Later
    # FIXME: 1 | 0  Comes from combinations if ganging is possible / True | False
    print("Litho Calculation Started  :" , len(df))
    df["Ganging"] = True



    litho_utilization = get_litho_utilization()
    df = df.merge(litho_utilization, "left", on=["Paper", "Sheet Size"])
    print(len(df))
    print(df["Ganging"].value_counts())


    df["Ganging Quantity"] = df["PagesNumber"] * df["Quantity"] * df["Ganging Utilization"]
    df["Ganging Sheets"] = df["Ganging Quantity"] / df["Placements"]
    df["Ganging Possible"] = (df["Ganging"]) & (df["Placements"] >= 2) & (
       df["Ganging Sheets"] <= 10000)


    df["Plates"] = np.where(df["Workstyle"].isin(["Simplex", "Sheetwise"]), df["Front_colour"] + df["Back_colour"], (df["Front_colour"]+df["Back_colour"])/2)
    df["Overs"] = df["Plates"] * 50

    df["Total Ganging Sheets"] = df["Ganging Sheets"] + df["Overs"]
    litho_machines = get_litho_machines()
    df = pd.merge(df,litho_machines,"left",on="Machine_size")
    df = df[df["Plates Costs"].isna() == False]
    df["Ganging Setup Cost"] = df["Setup Time"] * df["Plates"] / 60 * df["Cost"] + df["Total Ganging Sheets"] / df["Sheets / Hour"] * df["Cost"]
    df["Ganging Plates Cost"] = df["Plates"] * df["Plates Costs"]
    df["Ganging Litho Costs"] = df["Ganging Setup Cost"] + df["Plates Costs"]
    df["Ganging Paper Costs"] = df["Paper Costs"] * df["Total Ganging Sheets"]
    df["Ganging Printing and Paper Costs"] = df["Ganging Litho Costs"] + df["Ganging Paper Costs"]

    #NOTE: Normal Calculation

    df["Total Sheets"] = df["printing_sheets"] + df["Overs"]
    # litho_machines = get_litho_machines()
    df = df[df["Plates Costs"].isna() == False]
    df["Setup Cost"] = df["Setup Time"] * df["Plates"] / 60 * df["Cost"] + df["Total Sheets"] / df["Sheets / Hour"] * df["Cost"]
    df["Plates Cost"] = df["Plates"] * df["Plates Costs"]
    df["Litho Costs"] = df["Setup Cost"] + df["Plates Cost"]
    df["Paper Costs"] = df["Paper Costs"] * df["Total Sheets"]
    df["Printing and Paper Costs"] = df["Litho Costs"] + df["Paper Costs"]
    additional_prices, markup = get_additional()
    litho_additional = additional_prices[additional_prices["Attribute"].str.contains("Litho")].reset_index(drop=True)
    litho_additional = pd.merge(litho_additional, markup, "left", on="Supplier")
    litho_additional = litho_additional.rename({"value": "Additional"}, axis=1)
    litho_additional = litho_additional.drop("Attribute", axis=1)
    df = pd.merge(df, litho_additional, "left", on=["Supplier", "Machine_size"])
    del litho_additional
    df["Printing and Paper incl Markup"] = np.min(df[["Printing and Paper Costs", "Ganging Printing and Paper Costs"]] , axis=1) * (1 + df["Supplier Markup"] / 100) + df["Additional"]
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


    # df["Total Costs"] = df["Printing and Paper incl Markup"]  # FIX: Update Correct Values Later

    print("Litho Calculation Ended  :", len(df))
    print(df.memory_usage())
    print(df.dtypes)
    print(df["Quantity"].value_counts())
    return df
