import shutil
import sqlite3
from datetime import date, timedelta

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
DB = "data/inventory.db"
CSV = "data/processed/daily_sales.csv"

# code, name, category, price in Rs, shelf life in days, average units sold per day
FOODS = [
    ("FD-1001", "Toned Milk 500 ml pouch", "Dairy", 30, 3, 60),
    ("FD-1002", "Curd 400 g cup", "Dairy", 40, 7, 25),
    ("FD-1003", "Paneer 200 g", "Dairy", 90, 10, 12),
    ("FD-1004", "Sandwich Bread 400 g", "Bakery", 45, 5, 30),
    ("FD-1005", "Eggs tray of 12", "Dairy", 84, 21, 15),
    ("FD-1006", "Idli Dosa Batter 1 kg", "Chilled", 70, 4, 14),
    ("FD-1007", "Butter 100 g", "Dairy", 58, 120, 10),
    ("FD-1008", "Cheese Slices 200 g", "Dairy", 130, 90, 6),
    ("FD-1009", "Bananas 1 dozen", "Produce", 60, 4, 10),
    ("FD-1010", "Tomatoes 1 kg", "Produce", 40, 6, 18),
    ("FD-1011", "Fruit Juice 1 L", "Beverages", 110, 120, 7),
    ("FD-1012", "Potato Chips 52 g", "Snacks", 20, 120, 35),
    ("FD-1013", "Glucose Biscuits 100 g", "Snacks", 10, 180, 70),
    ("FD-1014", "Instant Noodles 70 g", "Snacks", 14, 240, 45),
    ("FD-1015", "Sunflower Oil 1 L", "Staples", 150, 270, 12),
]
WEEKDAY = {0: 0.9, 1: 0.9, 2: 0.95, 3: 1.0, 4: 1.15, 6: 1.35}  # Saturday is closed

conn = sqlite3.connect(DB)
if conn.execute("SELECT COUNT(*) FROM products WHERE stock_code LIKE 'FD-%'").fetchone()[0]:
    print("Food items already added. Nothing to do.")
    raise SystemExit
conn.close()

shutil.copy(DB, "data/inventory_backup_before_food.db")
shutil.copy(CSV, "data/processed/daily_sales_backup_before_food.csv")

conn = sqlite3.connect(DB)
cur = conn.cursor()
as_of = date.fromisoformat(cur.execute("SELECT value FROM settings WHERE key = 'as_of_date'").fetchone()[0])

if "category" not in [r[1] for r in cur.execute("PRAGMA table_info(products)")]:
    cur.execute("ALTER TABLE products ADD COLUMN category TEXT")
cur.execute("UPDATE products SET category = 'Gifts & home' WHERE category IS NULL")

hist = pd.read_csv(CSV, dtype={"StockCode": str}, parse_dates=["Date"])
open_days = [pd.Timestamp(d) for d in sorted(hist["Date"].unique())[-90:]]

new_hist, sales_rows, batch_rows = [], [], []
for code, name, cat, price, shelf, base in FOODS:
    cur.execute(
        "INSERT INTO products (stock_code, description, unit_price, shelf_life_days, category) VALUES (?, ?, ?, ?, ?)",
        (code, name, price, shelf, cat),
    )
    costs = [round(price * rng.uniform(0.72, 0.88), 2) for _ in range(3)]
    for supplier_id, c in zip((1, 2, 3), costs):
        cur.execute("INSERT INTO supplier_prices VALUES (?, ?, ?)", (supplier_id, code, c))
    avg_cost = round(float(np.mean(costs)), 2)

    for d in open_days:
        q = int(rng.poisson(base * WEEKDAY.get(d.dayofweek, 1.0)))
        new_hist.append((d, code, q))
        if q:
            hour = int(rng.integers(8, 21))
            sales_rows.append(("SIM", f"{d.date()} {hour:02d}:00:00", str(d.date()), code, q, price))

    # One fresh batch and one older batch
    for ago in (int(rng.integers(0, max(1, shelf // 3) + 1)), int(rng.integers(shelf // 2, shelf + 2))):
        received = as_of - timedelta(days=min(ago, 60))
        qty = max(3, int(base * rng.uniform(1, 3)))
        batch_rows.append((code, qty, received.isoformat(), (received + timedelta(days=shelf)).isoformat(), avg_cost))

cur.executemany(
    "INSERT INTO sales (invoice, sale_datetime, sale_date, stock_code, quantity, unit_price) VALUES (?, ?, ?, ?, ?, ?)",
    sales_rows,
)
cur.executemany(
    "INSERT INTO stock_batches (stock_code, quantity, received_date, expiry_date, cost_price) VALUES (?, ?, ?, ?, ?)",
    batch_rows,
)
conn.commit()

# The forecasting history needs the new products too
extra = pd.DataFrame(new_hist, columns=["Date", "StockCode", "Quantity"])
pd.concat([hist, extra]).to_csv(CSV, index=False, date_format="%Y-%m-%d")

today = as_of.isoformat()
soon = (as_of + timedelta(days=7)).isoformat()
print("Products now:", cur.execute("SELECT COUNT(*) FROM products").fetchone()[0])
print("Food sales rows added:", len(sales_rows))
print("Already expired batches:", cur.execute("SELECT COUNT(*) FROM stock_batches WHERE expiry_date < ?", (today,)).fetchone()[0])
print("Expiring in the next 7 days:", cur.execute(
    "SELECT COUNT(*) FROM stock_batches WHERE expiry_date BETWEEN ? AND ?", (today, soon)).fetchone()[0])
conn.close()