import pandas as pd
from pymongo import MongoClient
import itertools
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.environ["MONGO_URI"]
client = MongoClient(MONGO_URI)

# Creating DataFrame
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 5000)

attributes = client["Printulu"]["attributes"]
attributes = pd.DataFrame(attributes.find({}))
attributes = attributes.drop(["_id", "categories"], axis=1)


df_cols = ['Product Name', 'Product Code', 'Category', 'Pages', 'Finishing', 'Binding', 'Extra', 'Format', 'Quantity',
           'Refinement', 'Colour', 'Paper', 'Ganging Possible', 'Printing Markup', 'Finishing Markup', 'Binding Markup', 'Option Markup', 'Refinement Markup']
attributes_cols = ['Pages', 'Finishing', 'Binding', 'Extra',
                   'Format', 'Refinement', 'Colour', 'Paper']


def get_product_data(product_code: str) -> pd.DataFrame:
    db = client["Printulu"]
    products = db["products"]
    product_data = products.find_one({"product_code": product_code})
    printing_makrup = product_data["markup"]["Printing"]
    binding_markup = product_data["markup"]["Binding"]
    extra_markup = product_data["markup"]["Option"]
    finishing_markup = product_data["markup"]["Finishing"]
    refinement_markup = product_data["markup"]["Refinement"]
    options = [product_data[key] for key in ['category', 'pages', 'finishing', 'binding', 'extra', 'format', 'quantity', 'refinement', 'colour', 'paper']]
    combinations = list(itertools.product(*options))
    product_df = pd.DataFrame(combinations, columns=['category', 'pages', 'finishing', 'binding', 'extra', 'format', 'quantity', 'refinement', 'colour', 'paper'])
    product_df["Printing Markup"] = printing_makrup
    product_df["Binding Markup"] = binding_markup
    product_df["Option Markup"] = extra_markup
    product_df["Finishing Markup"] = finishing_markup
    product_df["Refinement Markup"] = refinement_markup
    product_df["Product Code"] = product_code
    product_df["Product Name"] = product_data["product_name"]
    product_df["Ganging Possible"] = product_data["ganging_possible"]
    return product_df


def create_combinations(product_code):
    product_df = get_product_data(product_code)
    product_df.columns = [col.title() for col in product_df.columns]
    new_cols = df_cols.copy()
    for col in product_df.columns:
        if col in attributes_cols:
            col_lookup = col.lower()
            attributes_product_df = attributes[attributes["type"] == col]
            attributes_product_df = attributes_product_df.drop_duplicates().reset_index(drop=True)
            merged = pd.merge(product_df, attributes_product_df, "left",right_on="name", left_on=col).reset_index(drop=True)
            col_codes = merged["code"]
            product_df[col_lookup] = col_codes
            new_cols.append(col_lookup) if col_lookup not in new_cols else None
    # TODO: Include Negative rules here
    return product_df[new_cols]


if __name__ == '__main__':
    create_combinations("tp_popcorn_box").to_csv("tp_popcorn_box.csv")
    pass
