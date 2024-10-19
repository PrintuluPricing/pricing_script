import pandas as pd
import glob

files = glob.glob("./*csv")

data = pd.concat([pd.read_csv(file).drop_duplicates().fillna("") for file in files])
print(len(data))
data = data.drop_duplicates()
print(len(data))
data.to_csv("Output final.csv", index=False)
