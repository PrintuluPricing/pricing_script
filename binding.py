import pandas as pd
import gspread
from helper_pricing import get_wiro_pur_binding_costs, get_wiro_thickness, get_wiro_length, get_pur_thickness, get_hanger_length, get_pur_quantity, get_wiro_pur_binding_costs

INPUT_PRICES_FOLDER = "1BrbtZ82ygpJ6Yu6m0nWboa2KN-rDe7PT"

key = "sheets_key_new.json"
service_acc = gspread.service_account(key)


def get_closest_thickness(thickness, binding_thickness):
    if thickness in binding_thickness:
        return thickness
    binding_thickness_bigger = [qty for qty in binding_thickness if qty > thickness]
    if thickness > max(binding_thickness):
        return max(binding_thickness)
    return sorted(binding_thickness_bigger)[0] if len(binding_thickness_bigger) > 0 else min(binding_thickness)


def get_closest_wiro_thickness(thickness):
    return get_closest_thickness(thickness, get_wiro_thickness())


def get_closest_pur_thickness(thickness):
    return get_closest_thickness(thickness, get_pur_thickness())


def get_closest_length(length, binding_length):
    if length in binding_length:
        return length
    binding_length_bigger = [qty for qty in binding_length if qty > length]
    if length > max(binding_length):
        return max(binding_length)
    return sorted(binding_length_bigger)[0] if len(binding_length_bigger) > 0 else min(binding_length)


def get_closest_wiro_length(length):
    return get_closest_length(length, get_wiro_length())


def get_closest_hanger_length(length):
    return get_closest_length(length, get_hanger_length())


def get_closest_quantities(quantity):
    pur_quantity = get_pur_quantity()
    if quantity in pur_quantity:
        return quantity
    pur_quantity_bigger = [qty for qty in pur_quantity if qty > quantity]
    if quantity > max(pur_quantity):
        return max(pur_quantity)
    return sorted(pur_quantity_bigger)[0] if len(pur_quantity_bigger) > 0 else min(pur_quantity)


def calculate_binding(df: pd.DataFrame) -> pd.DataFrame:
    df = df.reset_index(drop=True)
    df["Thickness"] = df["Paper GSM"].astype(int) * df["PagesNumber"].astype(int) / 2000 + 4
    df["Wiro Thickness"] = df["Thickness"].apply(get_closest_wiro_thickness).astype(str).str.replace("\.0","")
    df["Pur Thickness"] = df["Thickness"].apply(get_closest_pur_thickness).astype(str).str.replace("\.0","")
    df["Pur Thickness"] = df["Pur Thickness"].str.replace("\.0", "", regex=True)
    df["Wiro Thickness"] = df["Wiro Thickness"].str.replace("\.0", "", regex=True)
    df["Wiro Length"] = df["Length"].apply(get_closest_wiro_length).astype(str)
    df["Wiro Length"] = df["Wiro Length"].replace("\.0", "", regex=True)
    df["Hanger Length"] = df["Length"].apply(get_closest_hanger_length).astype(str)
    df["Hanger Length"] = df["Hanger Length"].replace("\.0", "", regex=True)
    df["Pur Quantity"] = df["Quantity"].apply(get_closest_quantities)

    wiro_prices = get_wiro_pur_binding_costs()[0]
    wiro_prices = df[["Binding", "Wiro Length", "Wiro Thickness", "Quantity"]].merge(wiro_prices, "left", left_on=["Binding", "Wiro Length", "Wiro Thickness"], right_on=["Attribute", "Length", "Thickness"])
    wiro_prices["Wiro Costs"] = wiro_prices["Setup"] + wiro_prices["value"] * wiro_prices["Quantity_x"]
    df["Wiro Costs"] = wiro_prices["Wiro Costs"].fillna(0)
    del (wiro_prices)

    pur_prices = get_wiro_pur_binding_costs()[5]
    pur_prices = df[["Binding", "Pur Thickness", "Quantity", "Pur Quantity"]].merge(pur_prices, "left", left_on=["Binding", "Pur Thickness", "Pur Quantity"], right_on=["Attribute", "Thickness", "Quantity"])
    pur_prices["Pur Costs"] = pur_prices["Setup"] + pur_prices["value"] * pur_prices["Quantity_x"]
    df["Pur Costs"] = pur_prices["Pur Costs"].fillna(0)
    del (pur_prices)

    hangers_prices = get_wiro_pur_binding_costs()[3]
    hangers_prices = df[["Binding", "Hanger Length", "Quantity"]].merge(hangers_prices, "left", left_on=["Binding", "Hanger Length"], right_on=["Attribute", "Length"])
    hangers_prices.to_csv("Hangers.csv", index=False)
    hangers_prices["Hangers Costs"] = hangers_prices["Setup"] + hangers_prices["value"] * hangers_prices["Quantity_x"]
    df["Hangers Costs"] = hangers_prices["Hangers Costs"].fillna(0)
    del (hangers_prices)
    df["Binding_costs"] = df["Wiro Costs"] + df["Hangers Costs"] + df["Pur Costs"]
    df["Binding_costs"] = df["Binding_costs"].fillna(0)
    df = df.reset_index(drop=True)
    return df


if __name__ == "__main__":
    length = get_closest_hanger_length(420)
    print(length)
    pass
