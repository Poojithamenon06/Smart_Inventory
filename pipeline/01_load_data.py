import pandas as pd

# The Excel file has two sheets (2009-2010 and 2010-2011)
sheets = pd.read_excel("data/raw/online_retail_II.xlsx", sheet_name=None)
df = pd.concat(sheets.values(), ignore_index=True)

print("Shape:", df.shape)
print(df.head())
print(df.dtypes)

df.to_csv("data/processed/retail_raw.csv", index=False)
print("Saved to data/processed/retail_raw.csv")