import pandas as pd
import numpy as np
from helper_pricing import get_additional, get_litho_machines


def calculation(df: pd.DataFrame)-> pd.DataFrame:
    # FIXME: Update Later
    # FIXME: 1 | 0  Comes from combinations if ganging is possible / True | False
    df["Ganging"] = True

    df["Ganging Quantity"] = df["PagesNumber"] * df["Quantity"]
    df["Ganging Sheets"] = df["Ganging Quantity"] / df["Placements"]
    df["Ganging Utilization"] = 0.5
    df["Ganging Possible"] = (df["Ganging"]) & (df["Placements"] >= 2) & (
       df["Ganging Sheets"] <= 10000)


    df["Plates"] = np.where(df["Workstyle"].isin(["Simplex", "Sheetwise"]), df["Front_colour"] + df["Back_colour"], (df["Front_colour"]+df["Back_colour"])/2)

    # TODO: Check Later Ganging calculation

    df["Total Ganging Sheets"] = df["Ganging Sheets"] + df["Overs"]
    litho_machines = get_litho_machines()
    df = pd.merge(df,litho_machines,"left",on="Machine_size")
    df = df[df["Plates Costs"].isna() == False]
    df["Ganging Setup Cost"] = df["Setup Time"] * df["Plates"] / 60 * df["Cost"] + df["Total Ganging Sheets"] / df["Sheets / Hour"] * df["Cost"]
    df["Ganging Plates Cost"] = df["Plates"] * df["Plates Costs"]
    df["Ganging Litho Costs"] = df["Ganging Setup Cost"] + df["Plates Cost"]
    df["Ganging Paper Costs"] = df["Paper Costs"] * df["Total Ganging Sheets"]
    df["Ganging Printing and Paper Costs"] = df["Ganging Litho Costs"] + df["Ganging Paper Costs"]

    #NOTE: Normal Calculation

    df["Overs"] = df["Plates"] * 50
    df["Total Sheets"] = df["printing_sheets"] + df["Overs"]
    litho_machines = get_litho_machines()
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
    df["Printing and Paper incl Markup"] = df["Printing and Paper Costs"] * (1 + df["Supplier Markup"] /100 ) + df["Additional"]

    return df
