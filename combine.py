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
products_data  = products_sheet.get()

# Creating DataFrame
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)
products = pd.DataFrame(products_data[1:],columns=products_data[0])
product_codes = list(set(list(products["productCode"])))

cols = ["Category","Product","Paper","Colour","Format","Finishing","Extra","Binding","Refinement","Quantity","Markup"]

for code in product_codes:
    data = products[products["productCode"]==code]
    data = data.drop_duplicates()
    data = data.pivot(index="productCode",columns="Type")
    data.columns = data.columns.droplevel()
    data["Product"] = code
    for col in data.columns:
        data[col] = data[col].str.split(";")
        data = data.explode(col)
        data[cols].to_csv(f"{code}_combinations.csv",index=False)
