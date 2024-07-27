import pandas as pd
import gspread


# Reading the products data from google sheets
key = "sheets_key_new.json"
service_acc = gspread.service_account(key)
attribute_sheet_id = "12cyM8-Azt8JhrytdE99p202bROfpb21QvONthrwHFVI"
attribute_sheet = service_acc.open_by_key(attribute_sheet_id)
products_sheet = attribute_sheet.worksheet("Product Combinations")
attribute_codes_sheet = attribute_sheet.worksheet("Attributes")
products_data = products_sheet.get()
attribute_data = attribute_codes_sheet.get()
negative_rules_sheet = attribute_sheet.worksheet("Negative Rules")
negative_rules_data = negative_rules_sheet.get()

# Creating DataFrame
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 5000)
products = pd.DataFrame(products_data[1:],columns=products_data[0])
product_codes = list(set(list(products["productCode"])))
attributes = pd.DataFrame(attribute_data[1:],columns=attribute_data[0])
negative_rules_data = pd.DataFrame(negative_rules_data[1:],columns=negative_rules_data[0])

cols = ["Category", "Product", "Sheets", "Paper", "Colour", "Format",
        "Finishing", "Extra", "Binding", "Refinement", "Quantity", "Printing Markup", "Finishing Markup", "Binding Markup", "Option Markup","Refinement Markup", "Ganging Possible"]
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
    negative_rules = negative_rules_data[negative_rules_data["Product Code"] == code]
    new_cols = cols.copy()
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
            new_cols.append(col_code_lookup[col])
    if len(negative_rules):
        negative_rules["Negative Rules"] = negative_rules["Negative Rules"].str.split("\n")
        negative_rules = negative_rules.explode("Negative Rules")
        negative_rules[["Rule1" ,"Rule2"]] = negative_rules["Negative Rules"].str.split("|", expand=True)
        negative_rules[["Category1" ,"Rule1"]] = negative_rules["Rule1"].str.split("-", expand=True)
        negative_rules[["Category2" ,"Rule2"]] = negative_rules["Rule2"].str.split("-", expand=True)
        negative_rules["Category1"] = negative_rules["Category1"].str.strip()
        negative_rules["Category2"] = negative_rules["Category2"].str.strip()
        negative_rules["Rule1"] = negative_rules["Rule1"].str.strip()
        negative_rules["Rule2"] = negative_rules["Rule2"].str.strip()
        for _, rule in negative_rules.iterrows():
            data = data[(data[rule["Category1"]] == rule["Rule1"]) & (data[rule["Category2"]] == rule["Rule2"]) == False]
    data[new_cols].to_csv(f"{code}_combinations.csv", index=False)
