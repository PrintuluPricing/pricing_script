import pandas as pd

data = pd.read_csv("tp_desk output_before.csv")

print(set(data["Category"]))
data = data[data["paper"] == "paper_250g_glossy"]
data = data[data["format"] == "format_14_8x21_h"]
# data = data[data["refinement"] == "refinement_lamination_matt_double"]
# data = data[data["Quantity"] == 15]

print(set(data["Category"]))

data.to_csv("tp_desk_checks_before.csv", index=False)

print(len(data))
