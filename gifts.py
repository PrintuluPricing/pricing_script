import pandas as pd
import numpy as np
from helper_pricing import get_weights, get_shipping_costs, get_finishing_costs, get_litho_sf_SQM


def calculation(df: pd.DataFrame)-> pd.DataFrame:
    df = df.reset_index(drop=True)
    print("Gifts Calculation Started  :", len(df))

    df["GSM"] =df["Paper"].str.extract("(\d+)gsm")
    df["GSM"] = pd.to_numeric(df["GSM"], errors="coerce")
    df["SQM"] = get_litho_sf_SQM(df["Format"])  # FIXME: Not Sure about SQM to get GSM, SQM should be based on sheet size, which sheet size to take if no printing
    finishing = get_finishing_costs()
    finishing = finishing[(finishing["value"].isna() == False) & (finishing["Supplier"] != "Quantity")]
    finishing = finishing.reset_index(drop=True)
    extra_costs = pd.merge(df[["Quantity", "Extra"]], finishing, "left", left_on="Extra", right_on="Attribute")
    extra_costs["Extra_costs"] = extra_costs["Setup-Cost"] + extra_costs["Quantity"] * extra_costs["value"]
    extra_costs["Extra_costs"] = np.where(extra_costs["Extra"] == "None", 0, extra_costs["value"] * extra_costs["Quantity"])
    df["Extra_costs"] = extra_costs["Extra_costs"]
    df["Supplier"] = extra_costs["Supplier"]


    weights = get_weights()
    extra_weights = weights[weights["Type"] == "Extra"]  # .reset_index(drop=True)
    extra_weights = df[["Extra"]].merge(extra_weights, "left", left_on="Extra", right_on="Attribute")
    df["Extra GSM"] = extra_weights["GSM"]
    del extra_weights
    df["Extra GSM"] = df["Extra GSM"].fillna(0)
    df["Total Weight"] = df["GSM"] * df["SQM"] + df["Extra GSM"]

# Shipping Costs

    shipping_costs = get_shipping_costs()
    df["Remaining"] = np.floor(df["Total Weight"] - shipping_costs["Minimum KG"])
    df["Remaining"] = np.where(df["Remaining"] < 0, 0, df["Remaining"])
    df["Shipping Costs"] = df["Remaining"] * shipping_costs["Kg After"] + shipping_costs["Minimum"]


    df["Total Costs"] = df["Extra_costs"] + df["Shipping Costs"]  # FIX: Update Correct Values Later

    print("Gifts Calculation Ended  :", len(df))
    df = df.reset_index(drop=True)
    return df
