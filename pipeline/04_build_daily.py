import pandas as pd

df = pd.read_csv(
    "data/processed/retail_clean.csv",
    dtype={"StockCode": str},
    parse_dates=["Date"],
)
summary = pd.read_csv("data/processed/product_summary.csv", dtype={"StockCode": str})

# Top 50 products by number of days sold
top_products = summary.sort_values("DaysSold", ascending=False).head(50)["StockCode"]
df = df[df["StockCode"].isin(top_products)]

# Days when the shop was open = days with any sale
open_days = sorted(pd.read_csv("data/processed/retail_clean.csv", parse_dates=["Date"])["Date"].unique())

# Quantity per product per day, with 0 on open days without a sale
daily = df.groupby(["Date", "StockCode"])["Quantity"].sum().unstack(fill_value=0)
daily = daily.reindex(open_days, fill_value=0)

daily.index.name = "Date"
daily_long = daily.reset_index().melt(
    id_vars="Date", var_name="StockCode", value_name="Quantity"
)

print("Open days:", len(open_days))
print("Products:", daily.shape[1])
print("Rows:", daily_long.shape)
print("Share of zero-sale rows:", round((daily_long["Quantity"] == 0).mean(), 3))
print(daily_long.head())

daily_long.to_csv("data/processed/daily_sales.csv", index=False)
print("Saved to data/processed/daily_sales.csv")