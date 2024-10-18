import pandas as pd
import glob

files = glob.glob("./*csv")

print(files)
for file in files:
    data = pd.read_csv(file)
    data["Category"] = data["Category"].fillna("")
    categories = list(set(list(data["Category"])))
    if categories == ['']:
        print(file)
        with open("Blank Combinations.txt", "a") as f:
            f.write(file + "\n")
