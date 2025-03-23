import pandas as pd
from helper_pricing_mongo import get_wiro, get_hanger, get_pur, get_wiro_thickness, get_wiro_length, get_pur_quantity, get_hanger_length, get_pur_thickness


def get_closest_thickness(thickness: float, binding_thickness: list[float]) -> float:
    if thickness in binding_thickness:
        return thickness
    binding_thickness = [float(thick) for thick in binding_thickness]
    binding_thickness_bigger = [qty for qty in binding_thickness if float(qty) >thickness]
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
    binding_length = [float(thick) for thick in binding_length]
    binding_length_bigger = [qty for qty in binding_length if float(qty) > length]
    if length > max(binding_length):
        return max(binding_length)
    return sorted(binding_length_bigger)[0] if len(binding_length_bigger) > 0 else min(binding_length)


def get_closest_wiro_length(length):
    return get_closest_length(length, get_wiro_length())


def get_closest_hanger_length(length):
    return get_closest_length(length, get_hanger_length())


def get_closest_quantities(quantity):
    pur_quantity = get_pur_quantity()
    pur_quantity = [float(thick) for thick in pur_quantity]
    if quantity in pur_quantity:
        return quantity
    pur_quantity_bigger = [qty for qty in pur_quantity if float(qty) > quantity]
    if quantity > max(pur_quantity):
        return max(pur_quantity)
    return sorted(pur_quantity_bigger)[0] if len(pur_quantity_bigger) > 0 else min(pur_quantity)


def calculate_binding(df: pd.DataFrame) -> pd.DataFrame:
    df = df.reset_index(drop=True)
    df["Thickness"] = df["Paper GSM"].astype(int) * df["PagesNumber"].astype(int) / 2000 + 4
    df["Wiro Thickness"] = df["Thickness"].apply(get_closest_wiro_thickness).astype(str).str.replace("\.0","")
    df["Pur Thickness"] = df["Thickness"].apply(get_closest_pur_thickness).astype(str).str.replace("\.0","")
    df["Pur Thickness"] = df["Pur Thickness"].str.replace("\.0", "", regex=True).astype(str)
    df["Wiro Thickness"] = df["Wiro Thickness"].str.replace("\.0", "", regex=True)
    df["Wiro Length"] = df["Length"].apply(get_closest_wiro_length).astype(str)
    df["Wiro Length"] = df["Wiro Length"].replace("\.0", "", regex=True)
    df["Hanger Length"] = df["Length"].apply(get_closest_hanger_length).astype(str)
    df["Hanger Length"] = df["Hanger Length"].replace("\.0", "", regex=True)
    df["Pur Quantity"] = df["Quantity"].apply(get_closest_quantities).astype(str)

    wiro_prices = get_wiro()[0]
    wiro_prices = df[["Binding", "Wiro Length", "Wiro Thickness", "Quantity"]].merge(wiro_prices, "left", left_on=["Binding", "Wiro Length", "Wiro Thickness"], right_on=["attribute", "length", "thickness"])
    wiro_prices["Wiro Costs"] = wiro_prices["setup"] + wiro_prices["price"] * wiro_prices["Quantity"]
    df["Wiro Costs"] = wiro_prices["Wiro Costs"].fillna(0)
    del (wiro_prices)

    pur_prices = get_pur()[0]
    pur_prices = df[["Binding", "Pur Thickness", "Quantity", "Pur Quantity"]].merge(pur_prices, "left", left_on=["Binding", "Pur Thickness", "Pur Quantity"], right_on=["attribute", "thickness", "quantity"])
    pur_prices["Pur Costs"] = pur_prices["setup"] + pur_prices["price"] * pur_prices["Quantity"]
    df["Pur Costs"] = pur_prices["Pur Costs"].fillna(0)
    del (pur_prices)

    hangers_prices = get_hanger()[0]
    hangers_prices = hangers_prices.drop_duplicates(["attribute", "length"]).reset_index(drop=True)
    hangers_prices = df[["Binding", "Hanger Length","idx", "Quantity"]].merge(hangers_prices, "left", left_on=["Binding", "Hanger Length",], right_on=["attribute", "length"])
    hangers_prices["Hangers Costs"] = hangers_prices["setup"] + hangers_prices["price"] * hangers_prices["Quantity"]
    df["Hangers Costs"] = hangers_prices["Hangers Costs"].fillna(0)
    del (hangers_prices)
    df["Binding_costs"] = df["Wiro Costs"].fillna(0) + df["Hangers Costs"].fillna(0) + df["Pur Costs"].fillna(0)
    df["Binding_costs"] = df["Binding_costs"].fillna(0)
    df = df.reset_index(drop=True)
    return df


if __name__ == "__main__":
    pass
