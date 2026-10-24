import pandas as pd

df = pd.read_csv(
    "data/processed/retail_raw.csv",
    dtype={"Invoice": str, "StockCode": str},
    parse_dates=["InvoiceDate"],
)
print("Start:", df.shape)

# 1. Remove exact duplicate rows
df = df.drop_duplicates()

# 2. Remove cancelled invoices (they start with "C")
df = df[~df["Invoice"].str.startswith("C")]

# 3. Remove zero or negative quantity and price
df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]

# 4. Remove rows with no product description
df = df.dropna(subset=["Description"])

# 5. Keep only real products (their stock codes start with 5 digits)
df = df[df["StockCode"].str.match(r"^\d{5}")]

# 6. Add helpful columns
df = df.rename(columns={"Customer ID": "CustomerID"})
df["Date"] = df["InvoiceDate"].dt.date
df["Revenue"] = df["Quantity"] * df["Price"]

print("After cleaning:", df.shape)
print("Date range:", df["Date"].min(), "to", df["Date"].max())
print("Unique products:", df["StockCode"].nunique())
print("Total revenue:", round(df["Revenue"].sum(), 2))

df.to_csv("data/processed/retail_clean.csv", index=False)
print("Saved to data/processed/retail_clean.csv")