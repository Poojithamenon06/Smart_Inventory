import os
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("reports", exist_ok=True)

df = pd.read_csv(
    "data/processed/retail_clean.csv",
    dtype={"StockCode": str},
    parse_dates=["Date"],
)

# Daily total quantity sold
daily = df.groupby("Date")["Quantity"].sum()
print("Days with sales:", len(daily))

# Average quantity by weekday (0 = Monday)
weekday = df.groupby(df["Date"].dt.dayofweek)["Quantity"].sum()
print("\nTotal quantity by weekday (0=Mon):")
print(weekday)

# Which products sell on the most days?
product_days = df.groupby("StockCode")["Date"].nunique()
product_qty = df.groupby("StockCode")["Quantity"].sum()
desc = df.groupby("StockCode")["Description"].first()

summary = pd.DataFrame(
    {"Description": desc, "DaysSold": product_days, "TotalQty": product_qty}
).sort_values("DaysSold", ascending=False)

print("\nTop 15 products by days sold:")
print(summary.head(15))

print("\nProducts sold on 300+ days:", (summary["DaysSold"] >= 300).sum())

# Chart 1: daily sales over time
plt.figure(figsize=(12, 4))
daily.plot()
plt.title("Daily total quantity sold")
plt.tight_layout()
plt.savefig("reports/daily_sales.png")

# Chart 2: top 10 products by quantity
plt.figure(figsize=(10, 5))
summary.sort_values("TotalQty", ascending=False).head(10)["TotalQty"].plot(kind="barh")
plt.title("Top 10 products by total quantity")
plt.tight_layout()
plt.savefig("reports/top_products.png")

summary.to_csv("data/processed/product_summary.csv")
print("\nSaved charts to reports/ and summary to data/processed/")