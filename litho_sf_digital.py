import pandas as pd
import numpy as np
from helper_pricing import get_placements


categories_sizes = {
    "Litho": ['45.5 x 64', '51 x 71', '64 x 91.5', '71 x 102'],
    "SF Digital": ['45.5 x 64', '32 x 45.5', '32 x 50', '32 x 64', '32 x 71', '32 x 91.5'],
    "LF Digital": ["100x100"],
}

categories_space = {
    "Litho": {"width": 15, "height": 5},
    "SF Digital": {"width": 1, "height": 1},
    "LF Digital": {"width": 5, "height": 5},
}


machine_sizes = {
    '45.5 x 64': "A2",
    '51 x 71': "A2",
    '64 x 91.5': "A1",
    '71 x 102': "A1",
    '32 x 45.5': "A3",
    '32 x 50': "A3",
    '32 x 64': "A3",
    '32 x 71': "A3",
    '32 x 91.5': "A3",
        }


def calculation(df: pd.DataFrame) -> pd.DataFrame:
    global machine_sizes
    global categories_sizes
    df["Sheet_size"] = ";".join(categories_sizes["Litho"] + categories_sizes["SF Digital"])
    df["Sheet_size"] = df["Sheet_size"].str.split(";")
    df = df.explode("Sheet_size")
    df["Machine_size"] = df["Sheet_size"].map(machine_sizes)

    # Litho Calculations
    # NOTE: Check whether to select sheetwise vs other workstyle and which to take by default
    df["Workstyle"] = np.where(df["Colour_code"].str[-1] == "0","Simplex","Sheetwise")
    df["Front_colour"] = df["Colour_code"].str.extract(r"colour_(\d)\d").astype(int)
    df["Back_colour"] = df["Colour_code"].str[-1].astype(int)

    # Calculating Placements
    df["Placements"] = df.apply(lambda x: get_placements(x["Format"], x["Sheet_size"]),axis=1)
    df = df[df["Placements"] > 0]
    df["printing_sheets"] = np.ceil(df["Quantity"] * df["PagesNumber"] / df[f"Placements"]).astype(int)
    return df
