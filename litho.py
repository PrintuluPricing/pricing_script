import pandas as pd
import numpy as np
from helper_pricing import read_google_sheet, get_additional, INPUT_PRICES_FOLDER


def calculation(df: pd.DataFrame)-> pd.DataFrame:
    df["Plates"] = np.where(df["Workstyle"].isin(["Simplex", "Sheetwise"]), df["Front_colour"] + df["Back_colour"], (df["Front_colour"]+df["Back_colour"])/2)
    df["Overs"] = df["Plates"] * 50
    df["Total Sheets"] = df["printing_sheets"] + df["Overs"]
    litho_machines = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Machine Costs")
    litho_machines = pd.melt(litho_machines, ["Attribute", "Category"],var_name="Supplier")
    litho_machines = litho_machines[litho_machines["value"] != ""]
    litho_machines["value"] = litho_machines["value"].astype(float)
    litho_machines["Machine_size"] = litho_machines["Attribute"].str.extract(r"(A\d)")
    litho_machines = pd.pivot(litho_machines,columns="Category",values="value",index=["Machine_size","Supplier"]).reset_index()
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
    return df
