import pandas as pd
import numpy as np
from helper_pricing import get_additional, get_litho_machines


def calculation(df: pd.DataFrame)-> pd.DataFrame:
    df["Plates"] = np.where(df["Workstyle"].isin(["Simplex", "Sheetwise"]), df["Front_colour"] + df["Back_colour"], (df["Front_colour"]+df["Back_colour"])/2)
    df["Overs"] = df["Plates"] * 50
    df["Total Sheets"] = df["printing_sheets"] + df["Overs"]
    litho_machines = get_litho_machines()
    df = pd.merge(df,litho_machines,"left",on="Machine_size")
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

    # FIXME: Update Later

    # df["Ganging Min Placements"] = 2
    # df["Ganging Max Sheets"] = 1000

    df["Ganging"] = True # FIXME: 1 | 0  Comes from combinations if ganging is possible / True | False

    df["Ganging Quantity"] = df["PagesNumber"] * df["Quantity"]
    df["Ganging Utilization"] = 0.5
    df["Ganging Possible"] =(df["Ganging"]) & (df["Placements"] >= 2) & (df["Quantity"] * df["PagesNumber"] / df["Placements"] <= 10000)
    return df
