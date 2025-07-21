import pandas as pd

data = pd.read_csv("tp_poster output_test.csv")

data = data[(data["format"] == "format_59_4x84_1") & (data["Quantity"] < 15)]
print(len(data))
data.to_csv("tp_poster_checks.csv", index=False)
