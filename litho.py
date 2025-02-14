import pandas as pd
import numpy as np
from helper_pricing_mongo import get_litho_machines, get_litho_utilization
from helper_pricing import get_weights, calculate_attributes
from shipping import calculate_shipping
from binding import calculate_binding



SHIPPING_MARKUP = 35
BINDING_NAMES = ["Wiro Binding - Black","Wiro Binding - Silver","Wiro Binding - White","Spiral Binding - Black","Spiral Binding - Silver","Spiral Binding - White","PUR Binding","A2 Wiro Binding - Black with Hanger","A2 Wiro Binding - Silver with Hanger","A2 Wiro Binding - White with Hanger","A3 Wiro Binding - Black with Hanger","A3 Wiro Binding - Silver with Hanger","A3 Wiro Binding - White with Hanger","A4 Wiro Binding - Black with Hanger","A4 Wiro Binding - Silver with Hanger","A4 Wiro Binding - White with Hanger"]

def printing_calculation(df: pd.DataFrame) -> pd.DataFrame:
    pass


# TODO: Include function later based on ganging condition

def ganging_calculation(df: pd.DataFrame) -> pd.DataFrame:
    df["Ganging Possible"] = (df["Ganging Possible"]) & (df["Placements"] >= 2) & (
       df["Quantity"] <= 10000)
    df["Total Ganging Sheets"] = df["Quantity"] + df["Overs"] / df["pages factor"]
    df["Total Ganging Sheets"] = df["Total Ganging Sheets"].astype('uint16')
    df["Ganging Paper Costs"] = df["Paper Costs"] * df["Total Ganging Sheets"] / df["Placements"] / df["utilization"]
    df["Ganging Setup Cost"] = (df["setup_time"] * df["Plates"] / 60 * df["cost_per_hour"] + df["Total Ganging Sheets"] / df["sheets_per_hour"] * df["cost_per_hour"]) / \
        df["Placements"] / df["utilization"]
    df["Ganging Plates Cost"] = df["Plates"] * df["plates_cost"] / df["Placements"] / df["utilization"]
    df["Ganging Litho Costs"] = df["Ganging Setup Cost"] + df["Ganging Plates Cost"]
    df["Ganging Printing and Paper Costs"] = df["Ganging Litho Costs"] + df["Ganging Paper Costs"]
    df["Ganging Additional"] = df["fixed_price"] / df["Placements"] / df["utilization"]
    return df


def overprinting_calculation(df: pd.DataFrame) -> pd.DataFrame:
    #TODO: Do the checks first in the calculation function

    # CHECK: Overprint is based on multiple and automatically calculated
    # df["Plates"] = np.where(df["OverPrintB"], df["Plates"] + df["Multiple"] - 1, df["Plates"])
    # df["Setup Time(hour)"] = df["Setup Time(hour)"] * np.where((df["OverPrintB"]) | (df["OverPrintFC"]), df["Multiple"], 1 )
    pass



def litho_calculation(df: pd.DataFrame) -> pd.DataFrame:
    # TODO: Check the calculation for litho based on specific inputs and apply to ganging?
    pass


def calculation(df: pd.DataFrame) -> pd.DataFrame:
    print("Litho Calculation Started  :", len(df))

    # NOTE: Precalculations
    df = df.reset_index(drop=True)

    bindings = np.sum(df["Binding"].isin(BINDING_NAMES))
    df["OverPrintB"] = df["Extra"].str.contains("Black Changes")
    df["OverPrintFC"] = df["Extra"].str.contains("Full Colour")
    df["Multiple"] = df["PagesNumber"] / df["Placements"] / df["pages factor"]
    df["Multiple"] = df["Multiple"].astype("float16")
    df["Multiple Log"] = df["Multiple"].astype("float16")
    df["Original Multiple"] = np.where(df["Product Code"] == "tp_notepad",  df["Multiple"].astype("float16"), np.where("pages factor" == 2, df["Multiple"] ,1))  # TODO: Check later
    df["Plates"] = np.where(df["Workstyle"].isin(["Simplex", "Sheetwise"]), df["front_colour"] + df["back_colour"], (df["front_colour"]+df["back_colour"])/2)
    df["Original Plates"] = df["Plates"]
    df["Plates"] = np.where(df["OverPrintB"], df["Plates"] + df["Multiple"] - 1, df["Plates"])
    df["Plates"] = np.where(df["OverPrintFC"], df["Plates"] * df["Multiple"] , df["Plates"])
    df["Plates"] = df["Plates"].astype("uint16")
    df["Overs"] = df["Plates"] * 50
    df["Overs"] = df["Overs"].astype("uint16")

    # NOTE: Loading inputs

    litho_utilization = get_litho_utilization()
    df = df.merge(litho_utilization, "left", on=["Paper", "sheet_size"])
    litho_machines = get_litho_machines()
    df = pd.merge(df,litho_machines,"left",on="machine")

    # CHECK: if the condition is still needed
    df = df[df["plates_cost"].isna() == False]

    # NOTE: Ganging refactoring
    ganging_check = df["Ganging Possible"].sum()
    if ganging_check > 0:
        # df = ganging_calculation(df)
        pass
    else:
        # df["Ganging Total"] = None  # CHECK: See whether to add the column or based on the condititon ignore the check of minuimum
        pass

    # NOTE: Ganging Calculation

    df["Ganging Possible"] = (df["Ganging Possible"]) & (df["Placements"] >= 2) & (
       df["Quantity"] <= 10000)
    df["Total Ganging Sheets"] = df["Quantity"] + df["Overs"]
    df["Total Ganging Sheets"] = df["Total Ganging Sheets"].astype('uint16')
    df["Ganging Paper Costs"] = df["Paper Costs"] * df["Total Ganging Sheets"] / df["Placements"] / df["utilization"]
    df["Ganging Setup Cost"] = (df["setup_time"] * df["Plates"] / 60 * df["cost_per_hour"] + df["Total Ganging Sheets"] / df["sheets_per_hour"] * df["cost_per_hour"]) / \
    df["Placements"] / df["utilization"]
    df["Ganging Plates Cost"] = df["Plates"] * df["plates_cost"] / df["Placements"] / df["utilization"]
    df["Ganging Litho Costs"] = df["Ganging Setup Cost"] + df["Ganging Plates Cost"]
    df["Ganging Printing and Paper Costs"] = df["Ganging Litho Costs"] + df["Ganging Paper Costs"]
    df["Ganging Printing Markup"] = df["Ganging Printing and Paper Costs"] * (1 + df["markup_percentage"] /100)
    df["Ganging Additional"] = df["fixed_price"] / df["Placements"] / df["utilization"]
    df["Ganging Total"] = df["Ganging Printing Markup"] + df["Ganging Additional"]

    # NOTE: Mutliple Sections Calclation

    df["printing_sheets"] = np.ceil(df["Quantity"] * df["Multiple"])
    df["Multiple"] = np.where((df["Multiple"] > 1) & df["pages factor"] == 1, 1, np.ceil(df["Multiple"])).astype("uint8")
    df["Total Sheets"] = df["printing_sheets"] + df["Overs"] * df["Multiple"]
    #NOTE: Normal Calculation

    df = df[df["plates_cost"].isna() == False]
    df = df.reset_index(drop=True)
    df["Setup Time(hour)"] = df["Plates"] * df["setup_time"] / 60 # CHECK: For same design setup is done once # * df["Original Multiple"]
    df["Setup Time(hour)"] = df["Setup Time(hour)"] * np.where((df["OverPrintB"]) | (df["OverPrintFC"]), df["Multiple"], 1 )
    df["Sheets Worked"] = df["Total Sheets"] / df["sheets_per_hour"]
    df["Setup Cost"] = df["Setup Time(hour)"] * df["cost_per_hour"] + df["Sheets Worked"] * df["cost_per_hour"]
    df["Plates Cost"] = df["Plates"] * df["plates_cost"] * df["Original Multiple"]
    df["Litho Costs"] = df["Setup Cost"] + df["Plates Cost"]
    df["Paper Costs"] = df["Paper Costs"] * df["Total Sheets"]
    df["Printing and Paper Costs"] = np.where((df["colour"] == "colour_00") | (df["pages"] == "sheets_0"),df["Paper Costs"], df["Litho Costs"] + df["Paper Costs"])
    df["Printing and Paper incl Markup"] = np.where((df["colour"] == "colour_00") | (df["pages"] == "sheets_0"),df["Paper Costs"], df["Litho Costs"] + df["Paper Costs"])
    df["fixed_price"] = df["fixed_price"] * df["Original Multiple"]
    df["Printing and Paper incl Markup"] = df["Printing and Paper incl Markup"] * (1 + df["markup_percentage"] / 100) + df["fixed_price"] * df["Multiple"]

    df["Printing and Paper incl Markup"] = np.where(df["Ganging Possible"], np.min(df[["Printing and Paper incl Markup", "Ganging Total"]] , axis=1),df["Printing and Paper incl Markup"])
    df = df[df["Printing and Paper incl Markup"].isna() == False]

    # NOTE: Cheapest Calculation
    cheapest = df[["idx", "sheet_size", "Printing and Paper incl Markup"]].groupby(["idx", "sheet_size"]).min("Printing and Paper incl Markup")
    cheapest = cheapest.reset_index()
    cheapest = cheapest.sort_values("Printing and Paper incl Markup", ascending=True).drop_duplicates("idx")
    cheapest = cheapest[["idx", "sheet_size"]]
    df = df.merge(cheapest,"inner",on=["idx","sheet_size"])
    del cheapest


# NOTE: Mutliple Sheets -> Cannot exceed the quantity
# NOTE: Brochures 8 Pages 1000 A4 portrait 100 gsm Gloss
# NOTE: Split for 2 4 pages sections for printing - example No Sections for 8 pages (45.5 x 64) -> 16 (pages) / 4 placements / 2 (because it's pages')
# NOTE: Sheets = Quantity (1000) * 16 (pages) / 4(placements)  / 2 (pages)

# NOTE: OverPrinting Calculation
# Black Changes Only
# Number of Schemes: pagesNum / placements / pages_factor
# Overs: 1 * Overs + (n_schemes - 1) * 50
# Plates: Plates + (n_schemes -1) * 1

    weights = get_weights()
    refinement_weights = weights[weights["Type"] == "Refinement"]  # .reset_index(drop=True)
    refinement_weights = df[["Refinement"]].merge(refinement_weights, "left", left_on="Refinement", right_on="Attribute")
    df["Refinement GSM"] = refinement_weights["GSM"]
    del refinement_weights
    extra_weights = weights[weights["Type"] == "Extra"]  # .reset_index(drop=True)
    extra_weights = df[["Extra"]].merge(extra_weights, "left", left_on="Extra", right_on="Attribute")
    df["Extra GSM"] = extra_weights["GSM"]
    del extra_weights
    df["Refinement GSM"] = df["Refinement GSM"].fillna(0) * df["Total Sheets"]
    df["Extra GSM"] = df["Extra GSM"].fillna(0) * df["Quantity"]
    df["GSM"] = df["GSM"] * df["Total Sheets"] + df["Refinement GSM"] + df["Extra GSM"]
    df["Total Weight"] = df["GSM"] * df["SQM"] / 1000
    df = df.sort_values("Printing and Paper incl Markup", ascending=True)
    df = df.drop_duplicates(["productpart", "paper", "format", "pages", "colour", "binding", "refinement", "finishing", "extra", "Quantity", "supplier"])
    df = df.reset_index(drop=True)

    # CHECK: Refinement, finishing and Extra weights

    df = calculate_shipping(df)
    if bindings > 0:
        df = calculate_binding(df)
    else:
        df["Binding_costs"] = 0
    df = calculate_attributes(df)
    df["Total Costs"] = df["Total Printing Costs"] + df["Refinement Costs"] + df["Extra Costs"] + df["Binding Costs"] + df["Finishing Costs"]
    df["Total Costs"] = np.where(df["Total Costs"] < 75, 75, df["Total Costs"])
    df["Shipping Costs"] = np.where(df["Shipping Costs"] < 100, 100, df["Shipping Costs"]) 
    df["Total Costs"] = df["Total Costs"] + df["Shipping Costs"]
    df = df[df["Total Costs"].isna() == False]
    df = df.sort_values("Total Costs", ascending=True)
    df = df.drop_duplicates(["productpart", "paper", "format", "pages", "colour", "binding", "refinement", "finishing", "extra", "supplier", "Quantity"])
    df = df.reset_index(drop=True)

    return df


if __name__ == "__main__":
    pass
