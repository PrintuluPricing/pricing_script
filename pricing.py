import pandas as pd
import glob
import sys
import warnings
from helper_pricing_mongo import get_dimensions
import litho_sf_digital
import litho
import sf_digital
import lf_digital
import gifts
import custom
import logging
from datetime import datetime
import numpy as np
from dotenv import load_dotenv
import os
from typing import Any

warnings.simplefilter(action="ignore")

pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)
pd.options.mode.use_inf_as_na = True

DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

load_dotenv()
log_level = logging.INFO

if DEBUG:
    log_level = logging.DEBUG

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


def loading_options() -> list[str]:
    args = sys.argv
    files = args[1:]
    return files


def return_first(args):
    return args[0]


timestamp = datetime.now().strftime("%d-%B-%y %H:%M")


def pricing_calculation(file:str| Any) -> dict[Any, Any]:

    data_columns = ['Category', 'Product Code', 'paper', 'format', 'pages', 'colors', 'book_binding', 'refinement', 'finishing', 'options', 'Printing Markup', 'Refinement Markup', 'Finishing Markup', 'Extra Markup', 'Binding Markup', 'SuperCategory', 'PagesIsSheets', 'Quantity', 'Binding', 'Finishing', 'Paper', 'Colour', 'Format', 'Refinement', 'Sheets', 'Extra', 'GangingQuantity']

    # FIXME: Check the consistent column names later
    data_columns = ['Category', 'Product Code', 'paper', 'format', 'pages', 'colour', 'binding', 'refinement', 'finishing', 'extra', 'Printing Markup', 'Refinement Markup', 'Finishing Markup', 'Extra Markup', 'Binding Markup', 'Quantity', 'Binding', 'Finishing', 'Paper', 'Colour', 'Format', 'Refinement', 'Sheets', 'Extra', 'Ganging Possible']

    columns = ["productpart", "paper", "format", "pages", "Quantity",
               "colors", "book_binding", "refinement", "finishing", "options", "file_type"]
    data = pd.read_csv(file, keep_default_na=False)
    logger.info(f"Received {len(data)} combinations")

    cat_columns = ['Category', 'Product Code', 'paper', 'format', 'pages', 'colors', 'book_binding', 'refinement', 'finishing', 'options',
                  'SuperCategory', 'Binding', 'Finishing', 'Paper', 'Colour', 'Refinement', 'Sheets', 'Extra']

    # FIXME: Check the consistent column names later
    cat_columns = ['Category', 'Product Code', 'paper', 'format', 'pages', 'colour', 'binding', 'refinement', 'finishing', 'extra',
                   'Binding', 'Finishing', 'Paper', 'Colour', 'Refinement', 'Pages', 'Extra']
    num_columns = ['Printing Markup', 'Refinement Markup', 'Finishing Markup', 'Extra Markup', 'Binding Markup']

    start = datetime.now()

    data[cat_columns] = data[cat_columns].astype('category')
    data[num_columns] = data[num_columns].astype('uint8')
    data["Quantity"] = data["Quantity"].astype('uint32')
    print(f"Casting took {datetime.now() - start}")
    # products = list(set(list(data["Product Code"])))
    data = data.rename({"Product": "Product Code"}, axis=1)

    print(len(data))
    print("Removing Duplicates")
    data = data.drop_duplicates(["Category","Product Code", "paper", "format", "pages", "colour", "binding", "refinement", "finishing", "extra", "Quantity"])
    unique = data.drop_duplicates(["Product Code", "paper", "format", "pages", "colour", "binding", "refinement", "finishing", "extra", "Quantity"]).reset_index(drop=True)
    unique = unique[["Product Code", "paper", "format", "pages", "colour", "binding", "refinement", "finishing", "extra", "Quantity"]]
    unique = unique.reset_index(drop=True)
    unique = unique.reset_index()
    unique = unique.rename({"index":"idx"}, axis=1)
    unique_combinations = len(unique)
    data = data.rename({"index":"idx"}, axis=1)
    data = data.reset_index(drop=True)
    data = data.merge(unique, "left", on=["Product Code", "paper", "format", "pages", "colour", "binding", "refinement", "finishing", "extra", "Quantity"])
    del unique
    print("Removed Duplicates")

    # with open(f"log_{timestamp}.txt", "a") as f:
    #     f.write(f" {unique_combinations} - unique records  | ")
    print(unique_combinations)
    categories = list(set(list(data["Category"])))
    print("Categories ", categories)
    data["file_type"] = "#"
    data["file_type"] = data["file_type"].astype('category')
    data["PagesNumber"] = data["pages"].str.extract(r"(\d+)")
    data["PagesNumber"] = pd.to_numeric(data["PagesNumber"], errors="coerce").astype('uint16', errors="ignore")
    data[["Height (cm)", "Width (cm)"]] = data["Format"].apply(
        get_dimensions).to_list()
    data[["Height (cm)", "Width (cm)"]] = data[["Height (cm)", "Width (cm)"]].astype('float16')
    data["Length"] = data["Height (cm)"] * 10
    data["Length"] = data["Length"].astype('float16')
    data["Format"] = data["Format"].astype("category")
    print("Adjusted all data")

    lf_digital_data = data[data["Category"] == "LF Digital"]
    litho_sf_digital_data = data[(data["Category"] == "Litho") | (data["Category"] == "SF Digital")]
    gifts_data = data[(data["Category"] == "Gifts") | (data["Category"] == "Gift")]
    custom_data = data[data["Category"].isin(["Litho", "SF Digital", "Gift"]) == False]
    print("Split categories")
    del data

    dfs = []
    if "Litho" in categories or "SF Digital" in categories:
        print("Adjusting Litho / SF Digital")
        litho_sf_digital_data = litho_sf_digital.calculation(litho_sf_digital_data)
        print("Finished Litho / SF Digital")

        print("Splitting Litho / SF Digital")
        litho_data = litho_sf_digital_data[litho_sf_digital_data["Category"] == "Litho"].reset_index(drop=True)
        sf_digital_data = litho_sf_digital_data[litho_sf_digital_data["Category"] == "SF Digital"]
        litho_data = litho_data.reset_index(drop=True)
        sf_digital_data = sf_digital_data.reset_index(drop=True)

        if len(litho_data) > 0:
            litho_data = litho.calculation(litho_data)
            # litho_data = calculate_binding(litho_data)
            # litho_data = calculate_attributes(litho_data, finishing)
            print("Litho Data!! ", len(litho_data))

            if len(litho_data) > 0:
                dfs.append(litho_data)
                del litho_data

        # SF Digital Calculation
        if len(sf_digital_data) > 0:
            sf_digital_data = sf_digital.calculation(sf_digital_data)
            # sf_digital_data = calculate_binding(sf_digital_data)
            # sf_digital_data = calculate_attributes(sf_digital_data, finishing)

            if len(sf_digital_data) > 0:
                dfs.append(sf_digital_data)
                del sf_digital_data

    if "LF Digital" in categories:
        print("Started LF Digital")
        lf_digital_data = lf_digital.calculation(lf_digital_data)
        if len(lf_digital_data) > 0:
            dfs.append(lf_digital_data)

    if "Gift" in categories or "Gifts" in categories:
        gifts_data = gifts.calculation(gifts_data)
        if len(gifts_data) > 0:
            dfs.append(gifts_data)

    # FIXME: This needs to be updated
    if "Custom" in categories:
        custom_data = custom.calculation(custom_data)
        print(len(custom_data), "Len Custom Data")
        if len(custom_data) > 0:
            dfs.append(custom_data)

    print("Collecting Data")
    if len(dfs) == 0:
        print(str(file), " No Data")
    try:
        output_data = pd.concat(dfs)
    except Exception as e:
        return ("Failed", {"df": "Concat Failed"})
    output_data = output_data.reset_index(drop=True)
    print(len(output_data), ": Len Output Data")
    print("Collected All")
    del dfs
    # output_data.to_csv(f"Output Data Before {products[0] if len(products) == 1 else None} {timestamp}.csv", index=False)
    # output_data[output_data["Total Costs"].isna()].to_csv(f"Output Data {products[0] if len(products) == 1 else None} {timestamp} no_prices.csv", index=False)
    failed_data = output_data[output_data["Total Costs"].isna() == True]
    output_data = output_data[output_data["Total Costs"].isna() == False]
    # NOTE: First remove_duplicates from the same combination and keep one for each supplier with the lowest cost
    # Need to check for the same category

    # NOTE: Checking the cheapest combinations before taking the max price
    output_data = output_data.reset_index(drop=True)
    output_data = output_data.sort_values("Total Costs", ascending=True)
    output_data = output_data.reset_index(drop=True)

    cheapest = output_data[["idx", "Category", "Total Costs"]].groupby(["idx", "Category"], as_index=False).min()
    # TODO: Do we actually need to sort?? the above already gets the cheapest !! Yes we do as one category can have multiple prices maybe
    cheapest = cheapest.sort_values("Total Costs", ascending=True).drop_duplicates("idx")
    cheapest = cheapest[["idx", "Category"]]
    output_data = output_data.merge(cheapest,"inner",on=["idx","Category"])
    del cheapest


    output_data = output_data.rename({"Product Code":"productpart", "colour":"colors", "binding":"book_binding", "extra": "options"}, axis=1)

    output_data = output_data.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "supplier", "Quantity"])
    print(len(output_data))
    output_data = output_data.sort_values("Total Costs", ascending=False)
    output_data = output_data.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Quantity"])
    # with open(f"log_{timestamp}.txt", "a") as f:
    #     f.write(f"Finished | {len(output_data)} - unique records \n")
    print(len(output_data))
    if len(output_data) == 0:
        logger.error("No Data")
            # return ("failed",failed_data.to_dict(orient='records'))
        return ("failed",failed_data.isna().sum().to_dict())
    output_data = output_data.reset_index(drop=True)
    # output_data.to_csv(f"Output Data {products[0] if len(products) == 1 else None} {timestamp}.csv", index=False)
    output_data = output_data.sort_values("Total Costs", ascending=False)
    output_data = output_data.drop_duplicates(columns)
    output_data = output_data.reset_index(drop=True)
    output_data["price"] = 1
    output_data["Unit Price"] = output_data["Total Costs"] / output_data["Quantity"]
    output_data["Unit Price"] = np.round(output_data["Unit Price"], 2).astype("float32")
    # output_data.to_csv(f"./output/Output Data {products[0] if len(products) == 1 else None} {timestamp} unit price.csv", index=False)
    final_data = pd.pivot_table(output_data, values="Unit Price", columns="Quantity", aggfunc="mean" , index=[
                             "price", "productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "file_type"])
    # final_data.to_csv(f"./output/Final Data  {products[0] if len(products) == 1 else None} - {timestamp}.csv")
    # print(f"Final Data returned from Main: {type(final_data)}")
    data_to_send = final_data.reset_index()
    return ("success", data_to_send.to_dict(orient='records'), final_data)


if __name__ == "__main__":
    files = glob.glob("./*tp*combinations.csv")
    print(files)
    if len(loading_options()) > 0:
        files = loading_options()
    for file in files:
        try:
            main([file])
        except Exception as e:
            print(e)
