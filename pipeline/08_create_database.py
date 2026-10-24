import sqlite3
import pandas as pd

df = pd.read_csv(
    "data/processed/retail_clean.csv",
    dtype={"StockCode": str, "Invoice": str},
    parse_dates=["InvoiceDate"],
)
summary = pd.read_csv("data/processed/product_summary.csv", dtype={"StockCode": str})

# Same 50 products the forecasting model was trained on
top = summary.sort_values("DaysSold", ascending=False).head(50)["StockCode"]
df = df[df["StockCode"].isin(top)]

# Products table: one row per product
products = (
    df.groupby("StockCode")
    .agg(description=("Description", "first"), unit_price=("Price", "median"))
    .reset_index()
)
products.columns = ["stock_code", "description", "unit_price"]
products["unit_price"] = products["unit_price"].round(2)

# Sales table: one row per sold line item
sales = df[["Invoice", "InvoiceDate", "StockCode", "Quantity", "Price"]].copy()
sales.columns = ["invoice", "sale_datetime", "stock_code", "quantity", "unit_price"]
sales["sale_date"] = sales["sale_datetime"].dt.strftime("%Y-%m-%d")
sales["sale_datetime"] = sales["sale_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

conn = sqlite3.connect("data/inventory.db")
conn.executescript("""
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS products;

CREATE TABLE products (
    stock_code  TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    unit_price  REAL NOT NULL
);

CREATE TABLE sales (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice       TEXT,
    sale_datetime TEXT NOT NULL,
    sale_date     TEXT NOT NULL,
    stock_code    TEXT NOT NULL REFERENCES products(stock_code),
    quantity      INTEGER NOT NULL,
    unit_price    REAL NOT NULL
);

CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_sales_product ON sales(stock_code);
""")

products.to_sql("products", conn, if_exists="append", index=False)
sales[["invoice", "sale_datetime", "sale_date", "stock_code", "quantity", "unit_price"]].to_sql(
    "sales", conn, if_exists="append", index=False
)
conn.commit()

# Quick checks
cur = conn.cursor()
print("Products:", cur.execute("SELECT COUNT(*) FROM products").fetchone()[0])
print("Sales rows:", cur.execute("SELECT COUNT(*) FROM sales").fetchone()[0])
print("\nTop 5 products by quantity sold:")
for row in cur.execute("""
    SELECT p.description, SUM(s.quantity) AS total_qty
    FROM sales s JOIN products p ON p.stock_code = s.stock_code
    GROUP BY s.stock_code ORDER BY total_qty DESC LIMIT 5
"""):
    print(row)
conn.close()
print("\nSaved to data/inventory.db")