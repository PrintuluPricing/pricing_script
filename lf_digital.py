import pandas as pd
import numpy as np
from helper_pricing_mongo import get_extra, get_lf_mahcines, get_lf_material, get_lf_SQM, get_refinement, get_weights, get_finishing, get_config, get_placements
from shipping import calculate_shipping


config = get_config()
# NOTE: Constants
SHIPPING_MARKUP = 35
SHIPPING_MARKUP = config['shipping_markup']
FIXED_EXTRA_HANDLING = 75  # R75 to be added to all extras
FIXED_EXTRA_HANDLING = config["extra_handling"]
FIXED_REFINEMENT_HANDLING = 50  # R50 to be added to all extras
FIXED_REFINEMENT_HANDLING = config["refinement_handling"]
FIXED_FINISHING_HANDLING = 25  # R25 to be added to all extras
FIXED_FINISHING_HANDLING = config["finishing_handling"]

def calculation(df: pd.DataFrame)-> pd.DataFrame:
    df = df.reset_index(drop=True)

    lf_printing_rates = get_lf_mahcines()
    df = df.merge(lf_printing_rates, "left", on="colour")

    df["SQM"] = df["format"].apply(get_lf_SQM).astype('float32')
    df["SQM"] = df["Quantity"] / df["SQM"]  # FIX: Check the integer ouptut
    df["Placements"] = df.apply(lambda x:  get_placements(x["format"], "100 x 100", "LF Digital"), axis=1)

    lf_material = get_lf_material()
    lf_double = list(lf_material[lf_material["double"] == True]["Paper"])
    lf_material = df.merge(lf_material, "left", on=["Paper", "supplier"])

    is_substrate = lf_material["substrate"].sum() > 0

    if is_substrate:
        substrate_data = lf_material[lf_material["substrate"]== True]
        substrate_data["Sides"] = np.where(substrate_data["colour"].str.contains("44"), "Double", "Single")
        substrate_data["Placements"] = substrate_data.apply(lambda x: get_placements(x["format"], x["dimensions"], "Litho"), axis=1 )
        substrate_data = substrate_data[substrate_data["Placements"] >= 1]
        substrate_data["Substrate Costs"] = np.where(substrate_data["Sides"] == "Double", substrate_data["double_side_printing"],substrate_data["single_side_printing"] )
        substrate_data = substrate_data.sort_values("Substrate Costs")
        substrate_data = substrate_data.drop_duplicates(["Paper", "idx"]).reset_index(drop=True)
        substrate_data = substrate_data[["idx","supplier", "substrate", "Substrate Costs"]]

    df["Waste %"] = lf_material["Waste %"].fillna(0)

    df["LF Double"] = np.where(df["Paper"].isin(lf_double),2,1)

    df["Printing Rate"] = df["Printing Rate"] * df["SQM"] * df["LF Double"]

    df["LF Cutting"] = lf_material["LF Cutting"]  # .fillna(0) * df["SQM"]
    df["LF Cutting"] = df["LF Cutting"].fillna(0) * df["SQM"]
    df["LF Cutting"] = df["LF Cutting"].astype(float)

    df["LF Material"] = lf_material["LF Material"]
    df["GSM"] = lf_material["GSM"]

    del lf_material

    df["LF Material"] = df["LF Material"] * df["SQM"] * df["LF Double"] * (df["Waste %"] + 1)
    df["Paper Costs"] = df["LF Material"] * df["LF Double"]
    df["Paper Costs"] = df["Paper Costs"].astype(float)
    df["Printing and Paper Costs"] = df["Printing Rate"] + df["LF Cutting"] + df["Paper Costs"]
    if is_substrate:
        df = df.merge(substrate_data, "left", on=["idx", "supplier"])
        df["Printing and Paper Costs"] = np.where(df["substrate"], df["Substrate Costs"] * df["SQM"] , df["Printing and Paper Costs"])

    lf_extra = get_extra()
    lf_extra = df[["Extra", "supplier", "Quantity"]].merge(lf_extra, "left", left_on=["Extra", "supplier"], right_on=["attribute", "supplier"])


    lf_extra["LF Extra"] = lf_extra["Quantity"] * lf_extra["price"] + lf_extra["setup"]

    df["LF Extra"] = lf_extra["LF Extra"]
    df["LF Extra"] = np.where(df["LF Extra"] > 0, df["LF Extra"] + FIXED_EXTRA_HANDLING, df["LF Extra"])
    df["LF Extra"] = np.where(df["Extra"] == "None", 0, df["LF Extra"])

    lf_refinement = get_refinement()
    lf_refinement = df.merge(lf_refinement, "left", on=["Refinement", "supplier"])

    df["LF Refinement"] = lf_refinement["price"]
    df["LF Refinement"] = np.where(df["Refinement"] == "None", 0, df["LF Refinement"])
    df["LF Refinement"] = df["LF Refinement"] * df["SQM"]
    df["LF Refinement"] = np.where(df["LF Refinement"] > 0, df["LF Refinement"] + FIXED_REFINEMENT_HANDLING, df["LF Refinement"])


    finishing = get_finishing()
    # FIXME: Remove the rename later
    finishing_costs = pd.merge(df[["supplier", "Quantity", "Finishing"]], finishing, "left", left_on=["supplier", "Finishing"], right_on=["supplier", "attribute"])
    finishing_costs["Finishing_costs"] = finishing_costs["setup"].fillna(0) +np.where(finishing_costs["price"] > 0,FIXED_FINISHING_HANDLING, 0)  + finishing_costs["Quantity"] * finishing_costs["price"]
    finishing_costs["Finishing_costs"] = np.where(finishing_costs["Finishing"] == "None",0, finishing_costs["Finishing_costs"])
    df["LF Finishing"] = finishing_costs["Finishing_costs"]


# Weight Calculation

    weights = get_weights()
    refinement_weights = weights[weights["Type"] == "Refinement"]  # .reset_index(drop=True)
    refiement_weights = df[["Refinement"]].merge(refinement_weights, "left", left_on="Refinement", right_on="Attribute")
    df["Refinement GSM"] = refiement_weights["GSM"]
    extra_weights = weights[weights["Type"] == "Extra"]  # .reset_index(drop=True)
    extra_weights = df[["Extra"]].merge(extra_weights, "left", left_on="Extra", right_on = "Attribute")
    df["Extra GSM"] = extra_weights["GSM"]
    df["Refinement GSM"] = df["Refinement GSM"].fillna(0)
    df["Extra GSM"] = df["Extra GSM"].fillna(0)
    df["GSM"] = df["GSM"].fillna(0) + df["Refinement GSM"] + df["Extra GSM"]
    df["GSM"] = df["GSM"].astype("float32")
    df["Total Weight"] = df["GSM"] * df["SQM"] / 1000

# Shipping Costs

    df = calculate_shipping(df)

    df["Total Printing Costs"] = df["Printing and Paper Costs"] * (1 + df["Printing Markup"]/100)
    df["Extra Costs"] = df["LF Extra"] * ( 1 + df["Extra Markup"]/100)
    df["Refinement Costs"] = df["LF Refinement"] * ( 1 + df["Refinement Markup"]/100)
    df["Finishing Costs"] = df["LF Finishing"] * ( 1 + df["Finishing Markup"]/100)
    df["Binding Costs"] = 0  # FIX: What about LF Binding??
    df["Total Costs"] = df["Total Printing Costs"] + df["Extra Costs"] + df["Refinement Costs"] + df["Finishing Costs"] + df["Binding Costs"]
    df["Total Costs"] = np.where(df["Total Costs"] < 75, 75, df["Total Costs"])
    df["Shipping Costs"] = np.where(df["Shipping Costs"] < 100, 100, df["Shipping Costs"]) 
    df["Total Costs"] = df["Total Costs"] + df["Shipping Costs"]

    print("LF Digital Ended: ", len(df))

    df = df.reset_index(drop=True)
    return df


if __name__ == "__main__":
    pass
