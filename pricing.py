import pandas as pd
import glob
import sys
import warnings
from binding import calculate_binding
from helper_pricing import get_finishing_costs, get_dimensions, get_SQM, calculate_attributes
import litho_sf_digital
import litho
import sf_digital
import lf_digital
from datetime import datetime

warnings.simplefilter(action="ignore")

pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)


def loading_options() -> list[str]:
    args = sys.argv
    files = args[1:]
    return files


def main(files: list[str]) -> pd.DataFrame:
    data_columns = ['Category', 'Product', 'paper', 'format', 'pages', 'colors', 'book_binding', 'refinement', 'finishing', 'options', 'Printing Markup', 'Refinement Markup', 'Finishing Markup', 'Option Markup', 'Binding Markup', 'SuperCategory', 'PagesIsSheets', 'Quantity', 'Binding', 'Finishing', 'Paper', 'Colour', 'Format', 'Refinement', 'Sheets', 'Extra']


    columns = ["price", "productpart", "paper", "format", "pages", "Quantity",
               "colors", "book_binding", "refinement", "finishing", "options", "file_type"]
    data = pd.concat(pd.read_csv(file, keep_default_na=False) for file in files)
    data = data[data_columns]
    cat_columns = ['Category', 'Product', 'paper', 'format', 'pages', 'colors', 'book_binding', 'refinement', 'finishing', 'options',
                  'SuperCategory', 'Binding', 'Finishing', 'Paper', 'Colour', 'Refinement', 'Sheets', 'Extra']

    num_columns = ['Printing Markup', 'Refinement Markup', 'Finishing Markup', 'Option Markup', 'Binding Markup',]# 'Quantity']

    start = datetime.now()
    data[cat_columns] = data[cat_columns].astype('category')
    data[num_columns] = data[num_columns].astype('uint8')
    data["Quantity"] = data["Quantity"].astype('int32')
    print(f"Casting took {datetime.now() - start}")
    products = list(set(list(data["Product"])))
    data = data.rename({"Product": "productpart"}, axis=1)

    print(len(data))
    data = data.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Quantity"])
    print(len(data))
    categories = list(set(list(data["Category"])))
    data["file_type"] = "#"
    data["file_type"] = data["file_type"].astype('category')
    data["PagesNumber"] = data["pages"].str.extract(r"(\d+)")
    data["PagesNumber"] = pd.to_numeric(data["PagesNumber"], errors="coerce").astype('uint16')
    data[["Height (cm)", "Width (cm)"]] = data["Format"].apply(
        get_dimensions).to_list()
    data[["Height (cm)", "Width (cm)"]] = data[["Height (cm)", "Width (cm)"]].astype('uint16')
    data["Length"] = data["Height (cm)"] * 10
    data["Length"] = data["Length"].astype('uint16')
    data["SQM"] = data["Format"].apply(get_SQM)
    data["Format"] = data["Format"].astype("category")

    lf_digital_data = data[data["Category"] == "LF Digital"]
    litho_sf_digital_data = data[(data["Category"] == "Litho") | (data["Category"] == "SF Digital")]
    finishing = get_finishing_costs()
    del data

    dfs = []
    if "Litho" in categories or "SF Digital" in categories:
        litho_sf_digital_data = litho_sf_digital.calculation(litho_sf_digital_data)
        # Splitting by category
        # Split Litho and SF Digital

        litho_data = litho_sf_digital_data[litho_sf_digital_data["Category"] == "Litho"].reset_index(drop=True)
        sf_digital_data = litho_sf_digital_data[litho_sf_digital_data["Category"] == "SF Digital"]
        litho_data = litho_data.reset_index(drop=True)
        sf_digital_data = sf_digital_data.reset_index(drop=True)
        litho_data = litho.calculation(litho_data)
        litho_data = calculate_attributes(litho_data, finishing)
        litho_data = calculate_binding(litho_data)

        if len(litho_data) > 0:
            dfs.append(litho_data)
            del litho_data
        # SF Digital Calculation
        sf_digital_data = sf_digital.calculation(sf_digital_data)
        sf_digital_data = calculate_attributes(sf_digital_data, finishing)
        sf_digital_data = calculate_binding(sf_digital_data)

        if len(sf_digital_data) > 0:
            dfs.append(sf_digital_data)
            del sf_digital_data

    if "LF Digital" in categories:
        #NOTE:  LF Digital Calculation
        lf_digital_data["SQM"] = lf_digital_data["Quantity"]/(10_000  / (lf_digital_data["SQM"] *10_000))
        #NOTE: Calculate printing Costs
        lf_digital_data = lf_digital.calculation(lf_digital_data)
        if len(lf_digital_data) > 0:
            dfs.append(lf_digital_data)

    print("Collecting Data")
    output_data = pd.concat(dfs)
    output_data = output_data.reset_index(drop=True)
    print("Collected All")
    del dfs
    output_data.to_csv(f"Output Data Before {products[0] if len(products) == 1 else None} {datetime.now()}.csv")
    output_data[output_data["Total Costs"].isna()].to_csv(f"Output Data {products[0] if len(products) == 1 else None} {datetime.now()} no_prices.csv")
    output_data = output_data[output_data["Total Costs"].isna() == False]
    print(len(output_data))
    output_data = output_data.sort_values("Total Costs", ascending=False)
    output_data = output_data.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Supplier", "Quantity"])
    print(len(output_data))
    output_data = output_data.sort_values("Total Costs", ascending=True)
    output_data = output_data.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Quantity"])
    print(len(output_data))
    output_data = output_data.reset_index(drop=True)
    output_data.to_csv(f"Output Data {products[0] if len(products) == 1 else None} {datetime.now()}.csv")
    output_data["Unit Price"] = output_data["Total Costs"] / output_data["Quantity"]
    output_data["price"] = 1
    output_data = output_data.sort_values("Total Costs", ascending=False)
    output_data = output_data.drop_duplicates(columns)
    output_data = pd.pivot_table(output_data, values="Unit Price", columns="Quantity", aggfunc="sum", index=[
                             "price", "productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "file_type"])
    output_data.to_csv(f"Final Data{datetime.now()}.csv")

    return output_data

# TODO: Cheapest combination for highest supplier
# TODO: Calculate OverPrinting for Deskpad
# TODO: Recalculate Ganging


if __name__ == "__main__":
    files = glob.glob("./*tp*combinations.csv")
    if len(loading_options()) > 0:
        files = loading_options()
    print(files)
    output = main(files)
