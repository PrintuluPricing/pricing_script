import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe

# Reading the products data from google sheets
key = "sheets_key_new.json"
service_acc = gspread.service_account(key)
attribute_sheet_id = "12cyM8-Azt8JhrytdE99p202bROfpb21QvONthrwHFVI"
attribute_sheet = service_acc.open_by_key(attribute_sheet_id)
products_sheet = attribute_sheet.worksheet("Product Combinations")
attribute_codes_sheet = attribute_sheet.worksheet("Attributes")
products_data = products_sheet.get()
attribute_data = attribute_codes_sheet.get()

# Creating DataFrame
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)
products = pd.DataFrame(products_data[1:],columns=products_data[0])
product_codes = list(set(list(products["productCode"])))
attributes = pd.DataFrame(attribute_data[1:],columns=attribute_data[0])

cols = ["Category", "Product", "Sheets", "Paper", "Colour", "Format",
        "Finishing", "Extra", "Binding", "Refinement", "Quantity", "Printing Markup", "Finishing Markup", "Binding Markup", "Option Markup","Refinement Markup"]
cols1 = ["Sheets", "Paper", "Colour", "Format",
        "Finishing", "Extra", "Binding", "Refinement"]

col_code_lookup = {
        "Paper": "paper",
        "Format": "format",
        "Sheets": "pages",
        "Colour": "colors",
        "Binding": "book_binding",
        "Refinement": "refinement",
        "Finishing": "finishing",
        "Extra": "options",
        }


for code in product_codes:
    data = products[products["productCode"] == code]
    data = data.drop_duplicates().reset_index(drop=True)
    data = data.pivot(index="productCode", columns="Type")
    data.columns = data.columns.droplevel()
    data["Product"] = code
    data = data.reset_index(drop=True)
    data[["Printing Markup", "Finishing Markup", "Binding Markup", "Option Markup", "Refinement Markup"]] = data["Markup"].str.split(";", expand=True)
    data = data.drop("Markup", axis=1)
    for col in data.columns:
        data[col] = data[col].str.split(";")
        data = data.explode(col)
        data = data.reset_index(drop=True)
        if col in cols1:
            attributes_data = attributes[attributes["Type"] == col].drop_duplicates().reset_index(drop=True)
            merged = pd.merge(data, attributes_data, "left",
                                 right_on="attribute_name", left_on=col).reset_index(drop=True)
            col_codes = merged["code"]
            # data[f"{col}_code"] = col_codes
            data[col_code_lookup[col]] = col_codes
            cols.append(col_code_lookup[col])
    data[cols].to_csv(f"{code}_combinations.csv", index=False)
