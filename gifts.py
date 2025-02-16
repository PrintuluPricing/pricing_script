import pandas as pd
import numpy as np
from helper_pricing_mongo import get_weights, get_finishing, get_litho_sf_SQM
from shipping import calculate_shipping


def calculation(df: pd.DataFrame) -> pd.DataFrame:
    df = df.reset_index(drop=True)
    print("Gifts Calculation Started  :", len(df))

    df["GSM"] = df["Paper"].str.extract("(\d+)gsm")
    df["GSM"] = pd.to_numeric(df["GSM"], errors="coerce")
    df["SQM"] = df["Format"].apply(get_litho_sf_SQM).astype('float32')

    finishing = get_finishing()
    finishing = finishing[(finishing["value"].isna() == False) & (finishing["Supplier"] != "Quantity")]
    finishing = finishing.reset_index(drop=True)

    extra_costs = pd.merge(df[["Quantity", "Extra", "idx"]], finishing, "left", left_on="Extra", right_on="Attribute")
    extra_costs["Extra_costs"] = extra_costs["Setup-Cost"].fillna(0) + extra_costs["Quantity"] * extra_costs["value"]
    extra_costs["Extra_costs"] = np.where(extra_costs["Extra"] == "None", 0, extra_costs["Extra_costs"])

    df = pd.merge(df, finishing, "left", left_on="Extra", right_on="Attribute")
    df["Extra_costs"] = df["Setup-Cost"].fillna(0) + df["Quantity"] * df["value"]
    df["Extra_costs"] = np.where(df["Extra"] == "None", 0, df["Extra_costs"])

    weights = get_weights()
    extra_weights = weights[weights["Type"] == "Extra"].reset_index(drop=True)
    extra_weights = df[["Extra"]].merge(extra_weights, "left", left_on="Extra", right_on="Attribute")
    df["Extra GSM"] = extra_weights["GSM"]
    del extra_weights
    paper_weights = weights[weights["Type"] == "Paper"].reset_index(drop=True)
    paper_weights = df[["Paper"]].merge(paper_weights, "left", left_on="Paper", right_on="Attribute")
    df["GSM"] = paper_weights["GSM"]
    df["GSM"].fillna(0)
    df["Extra GSM"] = df["Extra GSM"].fillna(0)
    df["Total Weight"] = df["GSM"] * df["SQM"] + df["Extra GSM"]

# Shipping Costs
    df = calculate_shipping(df)
    df["Total Costs"] = df["Extra_costs"] + df["Shipping Costs"]
    print("Gifts Calculation Ended  :", len(df))
    df = df.reset_index(drop=True)
    return df
