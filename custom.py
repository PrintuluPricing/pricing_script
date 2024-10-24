import pandas as pd
import numpy as np
from helper_pricing import get_custom
from shipping import calculate_shipping


def calculation(df: pd.DataFrame) -> pd.DataFrame:
    custom = get_custom()
    df = df.merge(custom, "left", on=["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "file_type"])
    df["Supplier"] = "Any"

    df["Total Costs"] = df["Quantity"] * df["Unit Price"] + df["Setup"]
    df["Total Weight"] = df["Quantity"] * df["Unit KG"]

    df = calculate_shipping(df)

    df["Total Costs"] = np.where(df["Total Costs"] < 75, 75, df["Total Costs"])
    df["Shipping Costs"] = np.where(df["Shipping Costs"] < 100, 100, df["Shipping Costs"]) 
    return df

