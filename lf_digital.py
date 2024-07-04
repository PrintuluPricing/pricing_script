import pandas as pd
import numpy as np
from helper_pricing import get_lf_cutting, get_lf_double, get_lf_mahcines, get_lf_material, get_lf_waste


def calculation(df: pd.DataFrame)-> pd.DataFrame:
    lf_printing_rates = get_lf_mahcines()
    df = df.merge(lf_printing_rates, "left", on="colors")
    lf_waste = get_lf_waste()
    df = df.merge(lf_waste, "left", on=["Supplier", "Paper"])
    df["Waste %"] = df["Waste %"].fillna(0)
    lf_double = get_lf_double()
    df["LF Double"] = np.where(df["Paper"].isin(lf_double),2,1)
    lf_cutting = get_lf_cutting()
    df = df.merge(lf_cutting, "left", on=["Supplier", "Paper"])
    df["LF Cutting"] = df["LF Cutting"].fillna(0) * df["SQM"]
    lf_material = get_lf_material()
    df = df.merge(lf_material, "left", on=["Paper", "Supplier"])
    # df["LF Material"] = df["LF Material"] * df["SQM"] * df["LF Double"] * (df["Waste %"] + 1)

    return df
