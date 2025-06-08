import pandas as pd
import numpy as np
from helper_pricing_mongo import get_placements, get_paper_costs, get_litho_sf_SQM, get_config


# TODO: update Printing Configuration from Database

printing_config = get_config()

categories_sizes = {
    "Litho": ";".join(['45.5 x 64', '51 x 71', '64 x 91.5', '71 x 102']),
    "SF Digital": ";".join(['45.5 x 64', '32 x 45.5', '32 x 50', '32 x 64', '32 x 71','51 x 71']),
    # "SF Digital": ";".join(['32 x 45.5', '32 x 50', '45.5 x 64']), #'32 x 64', '32 x 71', '32 x 91.5'],
    "LF Digital": "100x100",
}

# TODO: Remove Later
categories_space = {
    "Litho": {"width": 15, "height": 5},
    "SF Digital": {"width": 1, "height": 1},
    "LF Digital": {"width": 5, "height": 5},
}
categories_space = printing_config["categories_space"]

# TODO: Remove Later
machine_sizes = {
    "45.5 x 64": "A2",
    "51 x 71": "A2",
    "64 x 91.5": "A1",
    "71 x 102": "A1",
    "32 x 45.5": "A3",
    "32 x 50": "A3",
    "32 x 64": "A3",
    "32 x 71": "A3",
    "32 x 91.5": "A3",
        }
machine_sizes = printing_config["machine_sizes"]


def calculation(df: pd.DataFrame) -> pd.DataFrame:
    global machine_sizes
    global categories_sizes
    print("GSM Calculation")
    df["GSM"] =df["Paper"].str.extract("(\d+)gsm")
    df["GSM"] = pd.to_numeric(df["GSM"], errors="coerce")
    df["Paper GSM"] = df["GSM"].astype('float16')
    print("Sheet Size Calculation")


    df["sheet_size"] = df["Category"].map(categories_sizes)
    df["sheet_size"] = df["sheet_size"].str.split(";")
    df = df.explode("sheet_size")
    df["sheet_size"] = df["sheet_size"].astype('category')
    print("SQM Calculation")
    df["SQM"] = df["sheet_size"].apply(get_litho_sf_SQM).astype('float32')
    print("Machine Calculation")
    df["machine"] = df["sheet_size"].map(machine_sizes)
    df["machine"] = df["machine"].astype('category')

    # Litho Calculations
    # NOTE: Check whether to select sheetwise vs other workstyle and which to take by default
    df["Workstyle"] = np.where(df["colour"].str[-1] == "0","Simplex","Sheetwise")
    df["Workstyle"] = df["Workstyle"].astype('category')
    df["front_colour"] = df["colour"].str.extract(r"colour_(\d)\d").astype('uint8')
    df["back_colour"] = df["colour"].str[-1].astype('uint8')

    # Calculating Placements
    print("Placements Calculation")

    # df["Placements"] = df.apply(lambda x: get_placements(x["Format"], x["sheet_size"], x["Category"]), axis=1).astype('uint16')
    df["Placements"] = df.apply(lambda x: get_placements(x["format"], x["sheet_size"], x["Category"]), axis=1).astype('uint16')

    df = df[df["Placements"] > 0]

    print("Sheets")
    df["pages factor"] = np.where(df["pages"].str.contains("page"), 2, 1)
    df["pages"] = df["pages"].astype("category")

    # FIX: Calculate leaves and sheets based on pages / sheets / 2 if pages

    df["printing_sheets"] = np.ceil(df["Quantity"] * df["PagesNumber"] / df["Placements"]/ df["pages factor"] ).astype("uint32")
    paper_prices = get_paper_costs()
    df = pd.merge(df, paper_prices, "left", on=["Paper", "sheet_size"])
    del paper_prices
    df["Original Paper Costs"] = df["Paper Costs"].astype("float16")
    return df
