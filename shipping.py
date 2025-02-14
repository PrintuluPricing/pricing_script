import pandas as pd
import numpy as np
from helper_pricing_mongo import get_shipping_costs


SHIPPING_MARKUP = 35

def calculate_shipping(df: pd.DataFrame) -> pd.DataFrame:
    shipp = get_shipping_costs()
    shipping_costs1 = shipp.iloc[1,:]
    shipping_costs2 = shipp.iloc[2,:]
    shipping_costs3 = shipp.iloc[0,:]

    df["Remaining1"] = df["Total Weight"] - float(shipping_costs1["minimum_kg"])
    df["Remaining1"] = np.floor(df["Remaining1"])
    df["Remaining1"] = np.where(df["Remaining1"] < 0, 0, df["Remaining1"])
    df["Shipping Costs1"] = df["Remaining1"] * shipping_costs1["kg_after"] + shipping_costs1["minimum_cost"]


    df["Remaining2"] = df["Total Weight"] - float(shipping_costs2["minimum_kg"])
    df["Remaining2"] = np.floor(df["Remaining2"])
    df["Remaining2"] = np.where(df["Remaining2"] < 0, 0, df["Remaining2"])
    df["Shipping Costs2"] = df["Remaining2"] * shipping_costs2["kg_after"] + shipping_costs2["minimum_cost"]


    df["Remaining3"] = df["Total Weight"] - float(shipping_costs3["minimum_kg"])
    df["Remaining3"] = np.floor(df["Remaining3"])
    df["Remaining3"] = np.where(df["Remaining3"] < 0, 0, df["Remaining3"])
    df["Shipping Costs3"] = df["Remaining3"] * shipping_costs3["kg_after"] + shipping_costs3["minimum_cost"]

    df["Shipping Costs"] = np.min(df[["Shipping Costs1", "Shipping Costs2", "Shipping Costs3"]], axis=1)

    df["Shipping Costs"] = df["Shipping Costs"] * (1+ SHIPPING_MARKUP / 100)
    df["Shipping Costs"] = df["Shipping Costs"].astype("float32")

    # df = df.drop(["Remaining1", "Remaining2", "Remaining3", "Shipping Costs1", "Shipping Costs2", "Shipping Costs3"])

    return df
