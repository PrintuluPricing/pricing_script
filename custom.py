import pandas as pd
import numpy as np
# TODO: Custom Calculation
from helper_pricing_mongo import get_custom
from shipping import calculate_shipping


def calculation(df: pd.DataFrame) -> pd.DataFrame:
    custom = get_custom()
    df = df.rename({"Product Code": "product_code"}, axis=1)
    df = df.merge(custom, "left", on=["product_code", "paper", "format", "pages", "colour", "binding", "refinement", "finishing", "extra" ])
    df["supplier"] = "Any"

    df["Total Costs"] = df["Quantity"] * df["unit_price"] + df["setup"]
    # TODO: Make the markup dynamic
    df["Total Costs"] = df["Total Costs"] * 1.4
    df["Total Weight"] = df["Quantity"] * df["unit_kg"]

    df = calculate_shipping(df)

    df["Total Costs"] = np.where(df["Total Costs"] < 75, 75, df["Total Costs"])
    df["Shipping Costs"] = np.where(df["Shipping Costs"] < 100, 100, df["Shipping Costs"]) 
    df = df.rename({"product_code": "productpart"}, axis=1)
    return df

