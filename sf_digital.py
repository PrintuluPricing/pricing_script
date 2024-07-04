import pandas as pd
import numpy as np
from helper_pricing import get_additional, get_clicks


def calculation(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) == 0:
        return df
    df["Overs"] = np.where(df["Back_colour"] > 0, 4, 2)
    df["Total Sheets"] = df["printing_sheets"] + df["Overs"]
    clicks_costs = get_clicks()
    df = pd.merge(df, clicks_costs, "left", on=["Machine_size", "Workstyle"])
    df["Clicks Cost"] = df["Clicks Cost"] * df["Total Sheets"]
    df = df[df["Clicks Cost"] > 0]
    df["Paper Costs"] = df["Paper Costs"] * df["Total Sheets"]
    df["Printing and Paper Costs"] = df["Clicks Cost"] + df["Paper Costs"]
    additional_prices, markup = get_additional()
    sf_digital_additional = additional_prices[additional_prices["Attribute"].str.contains("SF - Digital")].reset_index(drop=True)
    sf_digital_additional = pd.merge(sf_digital_additional, markup, "left", on="Supplier")
    sf_digital_additional = sf_digital_additional.rename({"value": "Additional"}, axis=1)
    sf_digital_additional = sf_digital_additional.drop("Attribute", axis=1)
    df = pd.merge(df, sf_digital_additional, "left", on=["Supplier", "Machine_size"])
    df["Printing and Paper incl Markup"] = df["Printing and Paper Costs"] * (1 + df["Supplier Markup"] /100 ) + df["Additional"]
    return df
