import pandas as pd
import glob
import sys
import warnings
from binding import calculate_binding
from helper_pricing import get_finishing_costs, get_dimensions, calculate_attributes
import litho_sf_digital
import litho
import sf_digital
import lf_digital
import gifts
from datetime import datetime

warnings.simplefilter(action="ignore")

pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)


def loading_options() -> list[str]:
    args = sys.argv
    files = args[1:]
    return files

timestamp = datetime.now().strftime("%d-%B-%y %H:%M")

def main(files: list[str]) -> pd.DataFrame:
    print(timestamp)
    print(files)
    data_columns = ['Category', 'Product', 'paper', 'format', 'pages', 'colors', 'book_binding', 'refinement', 'finishing', 'options', 'Printing Markup', 'Refinement Markup', 'Finishing Markup', 'Option Markup', 'Binding Markup', 'SuperCategory', 'PagesIsSheets', 'Quantity', 'Binding', 'Finishing', 'Paper', 'Colour', 'Format', 'Refinement', 'Sheets', 'Extra', 'GangingQuantity']

    file_name = files[0].replace("/", "_")

    columns = ["price", "productpart", "paper", "format", "pages", "Quantity",
               "colors", "book_binding", "refinement", "finishing", "options", "file_type"]
    data = pd.concat(pd.read_csv(file, keep_default_na=False) for file in files)
    data = data[data_columns]
    cat_columns = ['Category', 'Product', 'paper', 'format', 'pages', 'colors', 'book_binding', 'refinement', 'finishing', 'options',
                  'SuperCategory', 'Binding', 'Finishing', 'Paper', 'Colour', 'Refinement', 'Sheets', 'Extra']

    num_columns = ['Printing Markup', 'Refinement Markup', 'Finishing Markup', 'Option Markup', 'Binding Markup', 'GangingQuantity']# 'Quantity']

    start = datetime.now()
    with open(f"log_{timestamp}.txt", "w+") as f:
        f.write(f"Started | {file_name} | {timestamp} \n")


    data[cat_columns] = data[cat_columns].astype('category')
    data[num_columns] = data[num_columns].astype('uint8')
    data["Quantity"] = data["Quantity"].astype('uint32')
    print(f"Casting took {datetime.now() - start}")
    products = list(set(list(data["Product"])))
    data = data.rename({"Product": "productpart"}, axis=1)

    print(len(data))
    print("Removing Duplicates")
    data = data.drop_duplicates(["Category","productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Quantity"])
    unique_combinations = len(data)
    print("Removed Duplicates")

    with open(f"log_{timestamp}.txt", "a") as f:
        f.write(f"{file_name} | {unique_combinations} - unique records \n")
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
    finishing = get_finishing_costs()
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
            litho_data = calculate_binding(litho_data)
            litho_data = calculate_attributes(litho_data, finishing)

            if len(litho_data) > 0:
                dfs.append(litho_data)
                del litho_data


        # SF Digital Calculation
        if len(sf_digital_data) > 0:
            sf_digital_data = sf_digital.calculation(sf_digital_data)
            sf_digital_data = calculate_binding(sf_digital_data)
            sf_digital_data = calculate_attributes(sf_digital_data, finishing)

            if len(sf_digital_data) > 0:
                dfs.append(sf_digital_data)
                del sf_digital_data

    if "LF Digital" in categories:
        lf_digital_data = lf_digital.calculation(lf_digital_data)
        if len(lf_digital_data) > 0:
            dfs.append(lf_digital_data)

    if "Gift" in categories or "Gifts" in categories:
        gifts_data = gifts.calculation(gifts_data)
        if len(gifts_data) > 0:
            dfs.append(gifts_data)

    print("Collecting Data")
    if len(dfs) == 0:
        print(files, " No Data")
    try:
        output_data = pd.concat(dfs)
    except:
        return
    output_data = output_data.reset_index(drop=True)
    print("Collected All")
    del dfs
    output_data.to_csv(f"Output Data Before {products[0] if len(products) == 1 else None} {timestamp}.csv", index=False)
    output_data[output_data["Total Costs"].isna()].to_csv(f"Output Data {products[0] if len(products) == 1 else None} {timestamp} no_prices.csv", index=False)
    output_data = output_data[output_data["Total Costs"].isna() == False]
    print(len(output_data))
    output_data = output_data.sort_values("Total Costs", ascending=True)
    output_data = output_data.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Supplier", "Quantity"])
    print(len(output_data))
    output_data = output_data.sort_values("Total Costs", ascending=False)
    output_data = output_data.drop_duplicates(["productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "Quantity"])
    with open(f"log_{timestamp}.txt", "a") as f:
        f.write(f"Finished | {file_name} | {len(output_data)} - unique records \n")
    print(len(output_data))
    output_data = output_data.reset_index(drop=True)
    output_data.to_csv(f"Output Data {products[0] if len(products) == 1 else None} {timestamp}.csv", index=False)
    output_data["Unit Price"] = output_data["Total Costs"] / output_data["Quantity"]
    output_data["price"] = 1
    output_data = output_data.sort_values("Total Costs", ascending=False)
    output_data = output_data.drop_duplicates(columns)
    output_data = pd.pivot_table(output_data, values="Unit Price", columns="Quantity", aggfunc="sum", index=[
                             "price", "productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "file_type"])
    output_data.to_csv(f"Final Data  {products[0] if len(products) == 1 else None} - {timestamp}.csv")

    return output_data

# TODO: Custom Products - Custom Products Sheet
# Pop
# Card
# Display
# Advertisement
# Promotion
# Mask
# Readd eliptical standee calculation


if __name__ == "__main__":
    files = glob.glob("./*tp*combinations.csv")
    if len(loading_options()) > 0:
        files = loading_options()
    for file in files[25:]:
        try:
            main([file])
        except error as e:
            with open("Failed Runs.txt", "a") as f:
                f.write(file+ "\n" + "\t" + e + "\n")
    # output = main(files)
