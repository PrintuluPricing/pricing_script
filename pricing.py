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

warnings.simplefilter(action="ignore")

pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)

# Loading Data
# TODO: Load data based on arguments, 1 product, all products

files = glob.glob("./*tp*combinations.csv")
print(files)
# FIX: Testing Only remove Later


def loading_options() -> None:
    args = sys.argv
    print(args)


def format_final_ouput(df: pd.DataFrame) -> pd.DataFrame:
    # FIXME: Check where in the script duplicates are being removed incorrectly or combinations are incorrect
    df["Unit Price"] = df["Total Costs"] / df["Quantity"]
    df["price"] = 1
    df = df.drop_duplicates(["price", "productpart", "paper", "format", "pages", "Quantity",
                            "colors", "book_binding", "refinement", "finishing", "options", "file_type"])
    df.to_csv(f"{file}_test_final_output.csv")
    df = pd.pivot_table(df, values="Unit Price", columns="Quantity", aggfunc="sum", index=[
                             "price", "productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "file_type"])
    return df


def main(file) -> None:
    data = pd.read_csv(file, keep_default_na=False)
    data = data.rename({"Product": "productpart"}, axis=1)
    categories = list(set(list(data["Category"])))
    data["file_type"] = "#"
    data["PagesNumber"] = data["Sheets"].str.extract(r"(\d+)").astype(int)
    # data["height_width"] = data["Format"].apply(get_dimensions)
    data[["Height (cm)", "Width (cm)"]] = data["Format"].apply(get_dimensions)[0]
    data["Length"] = data["Height (cm)"] * 10
    data["SQM"] = data["Format"].apply(get_SQM)
    # TODO: Calculate Overs!!!

    finishing = get_finishing_costs()

    if "Litho" in categories or "SF Digital" in categories:
        litho_sf_digital_data = data[(data["Category"] == "Litho") | (data["Category"] == "SF Digital")]
        litho_sf_digital_data = litho_sf_digital.calculation(litho_sf_digital_data)
        # Splitting by category
        # Split Litho and SF Digital
        litho_data = litho_sf_digital_data[litho_sf_digital_data["Category"] == "Litho"]
        sf_digital_data = litho_sf_digital_data[litho_sf_digital_data["Category"] == "SF Digital"]
        litho_data = litho.calculation(litho_data)
        litho_data = calculate_attributes(litho_data, finishing)
        litho_data = calculate_binding(litho_data)

        # SF Digital Calculation
        sf_digital_data = sf_digital.calculation(sf_digital_data)
        sf_digital_data = calculate_attributes(sf_digital_data, finishing)
        litho_data.to_csv("test_litho.csv",index=False)
        sf_digital_data.to_csv("test_sf_digital.csv", index=False)

    if "LF Digital" in categories:
        # LF Digital Calculation
        lf_digital_data = data[data["Category"] == "LF Digital"]
        lf_digital_data["SQM"] = lf_digital_data["Quantity"]/(10_000  / (lf_digital_data["SQM"] *10_000))
        # Calculate printing Costs
        lf_digital_data = lf_digital.calculation(lf_digital_data)
        lf_digital_data.to_csv(f"{file}_output.csv", index=False)
        format_final_ouput(lf_digital_data).to_csv(f"{file}_final_output.csv")


# TODO: Cheapest combination for highest supplier
# TODO: Add Refinement, Extra and Finishing Weight for litho and sf_digital
# TODO: Calculate Shipping Costs
# TODO: Calculate OverPrinting for Deskpad
# TODO: Recalculate Ganging


if __name__ == "__main__":
    for file in files:
        print(file)
        main(file)
        print(f"{file} done")
