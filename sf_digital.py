import pandas as pd
import numpy as np
from helper_pricing import read_google_sheet, get_additional, INPUT_PRICES_FOLDER


def calculation(df: pd.DataFrame)-> pd.DataFrame:
    df["Overs"] = np.where(df["Back_colour"] > -1 , 4 , 2 )
    df["Total Sheets"] = df["printing_sheets"] + df["Overs"]
    clicks_costs = read_google_sheet(INPUT_PRICES_FOLDER, "Input Prices", "Digital Clicks")
    clicks_costs = pd.melt(clicks_costs, "Attribute", var_name="Supplier", value_name="Clicks Cost")
    clicks_costs = clicks_costs[clicks_costs["Clicks Cost"]!= ""]
    clicks_costs["Machine_size"] = clicks_costs["Attribute"].str.extract(r"(A\d)")
    clicks_costs["Workstyle"] = clicks_costs["Attribute"].str.extract(r"\((.*)\)")
    clicks_costs["Clicks Cost"] = clicks_costs["Clicks Cost"].astype(float)
    clicks_costs = clicks_costs.drop("Attribute", axis=1)
    df = pd.merge(df, clicks_costs, "left", on=["Machine_size", "Workstyle"])
    df["Clicks Cost"] = df["Clicks Cost"] * df["Total Sheets"]
    df = df[df["Clicks Cost"] > -1]
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
