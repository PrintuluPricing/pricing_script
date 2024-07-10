import pandas as pd
import numpy as np
from helper_pricing import get_lf_cutting, get_lf_double, get_lf_mahcines, get_lf_material, get_lf_waste


def calculation(df: pd.DataFrame)-> pd.DataFrame:
    lf_printing_rates = get_lf_mahcines()
    lf_printing_rates = df.merge(lf_printing_rates, "left", on="colors")
    print(df.columns)
    df[["Supplier", "Printing Rate", "Machine"]] = lf_printing_rates[["Supplier", "Printing Rate", "Machine"]]
    lf_waste = get_lf_waste()
    lf_waste = df.merge(lf_waste, "left", on=["Supplier", "Paper"])
    df["Waste %"] = lf_waste["Waste %"].fillna(0)
    print(df.columns)
    lf_double = get_lf_double()
    df["LF Double"] = np.where(df["Paper"].isin(lf_double),2,1)
    print(df.columns)
    lf_cutting = get_lf_cutting()
    lf_cutting = df.merge(lf_cutting, "left", on=["Supplier", "Paper"])
    df["LF Cutting"] = lf_cutting["LF Cutting"].fillna(0) * df["SQM"]
    print(df.columns)
    lf_material = get_lf_material()
    lf_material = df.merge(lf_material, "left", on=["Paper", "Supplier"])
    df["LF Material"] = lf_material["LF Material"]
    print(df.columns)
    df["LF Material"] = df["LF Material"] * df["SQM"] * df["LF Double"] * (df["Waste %"] + 1)
    df["Printing and Paper Costs"] = df["Printing Rate"] + df["LF Cutting"] + df["LF Material"]

    return df
