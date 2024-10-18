import pandas as pd

notepad = pd.read_csv("Output Data tp_notepad 18-October-24 11:10.csv")
print(len(notepad))

notepad["Unit Price"] = notepad["Total Costs"] / notepad["Quantity"]

print(notepad[notepad["Quantity"] <5])

pivot = pd.pivot_table(notepad, values="Unit Price",columns="Quantity", aggfunc="sum",
index=[
                              "productpart", "paper", "format", "pages", "colors", "book_binding", "refinement", "finishing", "options", "file_type"])

pivot.to_csv("Pivot.csv")
