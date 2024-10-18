import pandas as pd
import numpy as np
from helper_pricing import get_additional, get_litho_machines, get_litho_utilization, get_weights, get_shipping_costs

SHIPPING_MARKUP = 35

def calculation(df: pd.DataFrame)-> pd.DataFrame:
    # FIXME: Update Later
    # FIXME: 1 | 0  Comes from combinations if ganging is possible / True | False
    df = df.reset_index(drop=True)
    print(df.columns)
    print("Litho Calculation Started  :", len(df))

    df["OverPrintB"] = df["Extra"].str.contains("Black Changes")
    df["OverPrintFC"] = df["Extra"].str.contains("Full Colour")
    df["pages factor"] = np.where(df["pages"].str.contains("page"),2,1)
    df["pages factor"] = df["pages factor"].astype('uint8')
    df["Multiple"] = df["PagesNumber"] / df["Placements"] / df["pages factor"]
    df["Multiple"] = df["Multiple"].astype("float16")
    df["Original Multiple"] = np.where(df["productpart"] == "tp_notepad",  df["Multiple"].astype("float16"),1)

    df["Ganging"] = df["GangingQuantity"] == 1
    df["Plates"] = np.where(df["Workstyle"].isin(["Simplex", "Sheetwise"]), df["Front_colour"] + df["Back_colour"], (df["Front_colour"]+df["Back_colour"])/2)
    df["Plates"] = np.where(df["OverPrintB"], df["Plates"] + df["Multiple"] - 1, df["Plates"])
    df["Plates"] = np.where(df["OverPrintFC"], df["Plates"] + df["Multiple"] - 1, df["Plates"])
    df["Plates"] = df["Plates"].astype("uint8")
    df["Overs"] = df["Plates"] * 50
    df["Overs"] = df["Overs"].astype("uint16")

    litho_utilization = get_litho_utilization()
    df = df.merge(litho_utilization, "left", on=["Paper", "Sheet Size"])
    litho_machines = get_litho_machines()
    df = pd.merge(df,litho_machines,"left",on="Machine_size")
    df = df[df["Plates Costs"].isna() == False]
    df[["Sheet Size", "Paper", "Machine_size"]]
    df.dtypes.to_csv("Dtypes Litho Machines Merge.csv")

    additional_prices, markup = get_additional()
    litho_additional = additional_prices[additional_prices["Attribute"].str.contains("Litho")].reset_index(drop=True)
    litho_additional = pd.merge(litho_additional, markup, "left", on="Supplier")
    litho_additional = litho_additional.rename({"value": "Additional"}, axis=1)
    litho_additional = litho_additional.drop("Attribute", axis=1)
    df = pd.merge(df, litho_additional, "left", on=["Supplier", "Machine_size"])
    del litho_additional

    df["Ganging Possible"] = (df["Ganging"]) & (df["Placements"] >= 2) & (
       df["Quantity"] <= 10000)
    df["Total Ganging Sheets"] = df["Quantity"] + df["Overs"]
    df["Total Ganging Sheets"] = df["Total Ganging Sheets"].astype('uint16')
    df["Ganging Paper Costs"] = df["Paper Costs"] * df["Total Ganging Sheets"] / df["Placements"] / df["Ganging Utilization"]
    df["Ganging Setup Cost"] = df["Setup Time"] * (df["Plates"] / 60 * df["Cost"] + df["Total Ganging Sheets"] / df["Sheets / Hour"] * df["Cost"]) / \
    df["Placements"] / df["Ganging Utilization"]
    df["Ganging Plates Cost"] = df["Plates"] * df["Plates Costs"] / df["Placements"] / df["Ganging Utilization"]
    df["Ganging Litho Costs"] = df["Ganging Setup Cost"] + df["Ganging Plates Cost"]
    df["Ganging Printing and Paper Costs"] = df["Ganging Litho Costs"] + df["Ganging Paper Costs"]

    df["Ganging Additional"] = df["Additional"] / df["Placements"] / df["Ganging Utilization"]

    # NOTE: Mutliple Sections Calclation

    # 12 / :q
    df["printing_sheets"] = np.ceil(df["Quantity"] * df["Multiple"])
    df["Multiple"] = np.where((df["Multiple"] > 1) & df["pages factor"] == 1, 1,
                              np.ceil(df["Multiple"])).astype("uint8")
    # df["Original Multiple"] = np.ceil(df["Original Multiple"])
    df["Total Sheets"] = df["printing_sheets"] + df["Overs"] * df["Multiple"]
    #NOTE: Normal Calculation

    df = df[df["Plates Costs"].isna() == False]
    df = df.reset_index(drop=True)
    df["Setup Time(hour)"] = df["Plates"] * df["Setup Time"] / 60 * df["Original Multiple"]
    df["Setup Time(hour)"] = df["Setup Time(hour)"] * np.where((df["OverPrintB"]) | (df["OverPrintFC"]), df["Multiple"], 1 )
    df["Sheets Worked"] = df["Total Sheets"] / df["Sheets / Hour"]
    df["Setup Cost"] = df["Setup Time(hour)"] * df["Cost"] + df["Sheets Worked"] * df["Cost"]
    # FIX: Check Setup Cost for Simplex / Sheetwise and Work and Turn
    df["Plates Cost"] = df["Plates"] * df["Plates Costs"] * df["Original Multiple"]
    df["Litho Costs"] = df["Setup Cost"] + df["Plates Cost"]
    df["Paper Costs"] = df["Paper Costs"] * df["Total Sheets"]  # FIXME: Paper Cost is overriten
    df["Printing and Paper Costs"] = df["Litho Costs"] + df["Paper Costs"]
    df["Printing and Paper incl Markup"] = np.where(df["Ganging"] & df["Ganging Possible"], np.min(df[["Printing and Paper Costs", "Ganging Printing and Paper Costs"]] , axis=1),df["Printing and Paper Costs"])

    df["Additional"] = df["Additional"] * df["Original Multiple"]

    df["Printing and Paper incl Markup"] = df["Printing and Paper incl Markup"] * (1 + df["Supplier Markup"] / 100) + df["Additional"] * df["Multiple"]
    df["Printing and Paper incl Markup"] = np.where(df["colors"] == "colour_00", 0, df["Printing and Paper incl Markup"])

    df = df[df["Printing and Paper incl Markup"].isna() == False]

# NOTE: Mutliple Sheets -> Cannot exceed the quantity
# NOTE: Brochures 8 Pages 1000 A4 portrait 100 gsm Gloss
# NOTE: Split for 2 4 pages sections for printing - example No Sections for 8 pages (45.5 x 64) -> 16 (pages) / 4 placements / 2 (because it's pages')
# NOTE: Sheets = Quantity (1000) * 16 () / 4(placements)  / 2 (pages)

# NOTE: OverPrinting Calculation
# Black Changes Only
# Number of Schemes: pagesNum / placements / pages_factor
# Overs: 1 * Overs + (n_schemes - 1) * 50
# Plates: Plates + (n_schemes -1) * 1

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

    #FIX: Check Refinement, finishing and Extra weights

# Shipping Costs

    shipping_costs = get_shipping_costs()
    df["Remaining"] = np.floor(df["Total Weight"] - shipping_costs["Minimum KG"])
    df["Remaining"] = np.where(df["Remaining"] < 0, 0, df["Remaining"])
    df["Shipping Costs"] = df["Remaining"] * shipping_costs["Kg After"] + shipping_costs["Minimum"]
    df["Shipping Costs"] = df["Shipping Costs"] * (1+ SHIPPING_MARKUP / 100)
    df["Shipping Costs"] = df["Shipping Costs"].astype("float32")


    # df["Total Costs"] = df["Printing and Paper incl Markup"]  # FIX: Update Correct Values Later

    # df.to_csv("Litho Calculation.csv", index=False)
    df = df.sort_values("Printing and Paper incl Markup", ascending=True)
    df = df.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Quantity", "Supplier"])
    # df = df.sort_values("Printing and Paper incl Markup", ascending=False)
    # df = df.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Quantity"])


    df = df.reset_index(drop=True)
    return df
