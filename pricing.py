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
file_test = files[2]


def loading_options() -> None:
    args = sys.argv
    print(args)


def main() -> None:
    data = pd.read_csv(file_test, keep_default_na=False)
    print(data.memory_usage())
    exit()
    categories = list(set(list(data["Category"])))
    data["PagesNumber"] = data["Sheets"].str.extract(r"(\d+)").astype(int)
    data["GSM"] = data["Paper"].str.extract("(\d+)gsm")
    # data["height_width"] = data["Format"].apply(get_dimensions)
    data[["Height (cm)", "Width (cm)"]] = data["Format"].apply(get_dimensions)[0]
    data["Length"] = data["Height (cm)"] * 10
    data["SQM"] = data["Format"].apply(get_SQM)

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
        lf_digital_data["SQM"] = lf_digital_data["Quantity"] / lf_digital_data["SQM"]
        # Calculate printing Costs
        lf_digital_data = lf_digital.calculation(lf_digital_data)
        lf_digital_data.to_csv("test_lf_digital.csv")


# TODO: Shipping Prices
# TODO: Cheapest combination for highest supplier
# TODO: Exclude Suppliers missing combination prices




if __name__ == "__main__":
    main()
    # loading_options()


