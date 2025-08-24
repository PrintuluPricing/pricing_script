import pandas as pd
from pymongo import MongoClient
import itertools
from dotenv import load_dotenv
import os
import logging

load_dotenv()

DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
MONGO_URI = os.environ["MONGO_URI"]
client = MongoClient(MONGO_URI)

# Creating DataFrame
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 5000)

attributes = client["Printulu"]["attributes"]
attributes = pd.DataFrame(attributes.find({},{"_id":0,"type":1,"name":1,"code":1}))


log_level = logging.INFO
if DEBUG:
    log_level = logging.DEBUG

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


df_cols = ['Product Name', 'Product Code', 'Category', 'Pages', 'Finishing', 'Binding', 'Extra', 'Format', 'Quantity',
           'Refinement', 'Colour', 'Paper', 'Ganging Possible', 'Printing Markup', 'Finishing Markup', 'Binding Markup', 'Extra Markup', 'Refinement Markup', "Custom Price"]
attributes_cols = ['Pages', 'Finishing', 'Binding', 'Extra',
                   'Format', 'Refinement', 'Colour', 'Paper']


def get_product_data(product_code: str) -> pd.DataFrame:
    db = client["Printulu"]
    products = db["products"]
    product_data = products.find_one({"product_code": product_code, "active":True})
    global_rules = db["settings"].find_one({"type":"Incompatibility Rules"})["incompatibility_rules"]
    rules = product_data.get("incompatibility_rules",[])
    rules.extend(global_rules)
    options = [product_data[key] for key in ['category', 'pages', 'finishing', 'binding', 'extra', 'format', 'quantity', 'refinement', 'colour', 'paper']]
    combinations = list(itertools.product(*options))
    product_df = pd.DataFrame(combinations, columns=['category', 'pages', 'finishing', 'binding', 'extra', 'format', 'quantity', 'refinement', 'colour', 'paper'], dtype='category')
    for rule in rules:
        rule_col = rule['type'].lower()
        attribute = rule['option']
        for incompatible in rule["incompatible_with"]:
            incompatible_column = incompatible["type"].lower()
            incompatible_attribute = int(incompatible["option"]) if incompatible_column == "quantity" else incompatible["option"]
            product_df = product_df[(product_df[rule_col] == attribute) & (product_df[incompatible_column] == incompatible_attribute)  == False]

    product_df = product_df.reset_index(drop=True)
    printing_makrup = product_data["markup"]["Printing"]
    binding_markup = product_data["markup"]["Binding"]
    extra_markup = product_data["markup"]["Extra"]
    finishing_markup = product_data["markup"]["Finishing"]
    refinement_markup = product_data["markup"]["Refinement"]
    product_df["Printing Markup"] = printing_makrup
    product_df["Binding Markup"] = binding_markup
    product_df["Extra Markup"] = extra_markup
    product_df["Finishing Markup"] = finishing_markup
    product_df["Refinement Markup"] = refinement_markup
    product_df["Product Code"] = product_code
    product_df["Product Name"] = product_data["product_name"]
    product_df["Ganging Possible"] = product_data.get("ganging_possible", False)
    product_df["Custom Price"] = product_data.get("unit_price", False)
    return product_df, product_data


def create_combinations(product_code, debug=DEBUG):
    product_df, product_data = get_product_data(product_code)
    product_df.columns = [col.title() for col in product_df.columns]
    new_cols = df_cols.copy()
    for col in product_df.columns:
        if col in attributes_cols:
            col_lookup = col.lower()
            attributes_product_df = attributes[(attributes["type"] == col) & (attributes["code"].isin(product_data[f"{col.lower()}_code"]))]
            attributes_product_df = attributes_product_df.drop_duplicates().reset_index(drop=True)
            merged = pd.merge(product_df, attributes_product_df, "left",right_on="name", left_on=col).reset_index(drop=True)
            col_codes = merged["code"]
            product_df[col_lookup] = col_codes
            new_cols.append(col_lookup) if col_lookup not in new_cols else None
    if product_df.isna().sum().sum() > 0 and not DEBUG:
        logger.error(product_df.isna().sum()[product_df.isna().sum() > 0])
        raise Exception(f"Some Codes Weren't Found : {product_df.isna().sum()[product_df.isna().sum() > 0]}")
    return product_df[new_cols]


if __name__ == '__main__':
    pass
