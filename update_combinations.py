import pandas as pd
import gspread
import glob

combinations = glob.glob("./all_combinations/*csv")

file = combinations[0]

data = pd.read_csv(file, keep_default_na=False)

product_code = list(set(data["Product"]))[0]

finishing = ";".join(list(set(data["Finishing"])))
paper = ";".join(list(set(data["Paper"])))
binding = ";".join(list(set(data["Binding"])))
extra = ";".join(list(set(data["Extra"])))
format = ";".join(list(set(data["Format"])))
quantity = ";".join([str(q).replace(".0","") for q in list(set(data["Quantity"]))])
refinement = ";".join(list(set(data["Refinement"])))
colour = ";".join(list(set(data["Colour"])))
category = ";".join(list(set(data["Category"])))
sheets = ";".join(list(set(data["Sheets"])))
ganging = ";".join([str(q).replace(".0","") for q in list(set(data["GangingQuantity"]))])
print(ganging)
print(bool(int(ganging)))



# TODO: Markups
