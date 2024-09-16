import pandas as pd
import numpy as np
from helper_pricing import get_lf_cutting, get_lf_double, get_lf_extra, get_lf_mahcines, get_lf_material, get_lf_waste


def calculation(df: pd.DataFrame)-> pd.DataFrame:
    lf_printing_rates = get_lf_mahcines()
    lf_printing_rates = df.merge(lf_printing_rates, "left", on="colors")
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
    df = df[df["LF Material"].isna()== False].reset_index(drop=True)
    df["Printing and Paper Costs"] = df["Printing Rate"] + df["LF Cutting"] + df["LF Material"]
    lf_extra = get_lf_extra()
    lf_extra = df.merge(lf_extra, "left", on=["Extra", "Supplier"])
    lf_extra.to_csv("LF Extra.csv", index=False)
    df["LF Extra"] = lf_extra["LF Extra"]
    df["LF Extra"] = df["LF Extra"] * df["Quantity"]
    df = df[df["LF Extra"].isna()== False].reset_index(drop=True)
    df["Paper Weight"] = df["GSM"] * df["SQM"] / 1000
    df["Printing and Paper Markup"] = df["Printing and Paper Costs"] * (1 + df["Printing Markup"]/100)
    df["LF Extra Markup"] = df["LF Extra"] * ( 1 + df["Option Markup"]/100)
    df["Total Costs"] = df["Printing and Paper Markup"] + df["LF Extra Markup"]

    return df
