import pandas as pd
import numpy as np
# TODO: Custom Calculation
from helper_pricing_mongo import get_custom
from shipping import calculate_shipping


def calculation(df: pd.DataFrame) -> pd.DataFrame:
    custom = get_custom()
    print(custom.columns)
    df = df.rename({"Product Code": "productpart"}, axis=1)
    print(df.columns)
    df = df.merge(custom, "left", on=["productpart", "paper", "format", "pages", "colour", "binding", "refinement", "finishing", "extra" ])
    df["supplier"] = "Any"

    df["Total Costs"] = df["Quantity"] * df["unit_price"] + df["setup"]
    df["Total Weight"] = df["Quantity"] * df["unit_kg"]

    df = calculate_shipping(df)

    df["Total Costs"] = np.where(df["Total Costs"] < 75, 75, df["Total Costs"])
    df["Shipping Costs"] = np.where(df["Shipping Costs"] < 100, 100, df["Shipping Costs"]) 
    return df

