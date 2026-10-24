import sqlite3
import numpy as np
import pandas as pd
from datetime import date, timedelta

rng = np.random.default_rng(42)  # fixed seed = same data every run
conn = sqlite3.connect("data/inventory.db")
cur = conn.cursor()

as_of = date(2011, 12, 10)  # the day after the last sale in the dataset

cur.executescript("""
DROP TABLE IF EXISTS stock_batches;
DROP TABLE IF EXISTS supplier_prices;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS settings;

CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE suppliers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    lead_time_days INTEGER NOT NULL
);
CREATE TABLE supplier_prices (
    supplier_id INTEGER REFERENCES suppliers(id),
    stock_code  TEXT REFERENCES products(stock_code),
    cost_price  REAL NOT NULL,
    PRIMARY KEY (supplier_id, stock_code)
);
CREATE TABLE stock_batches (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code    TEXT REFERENCES products(stock_code),
    quantity      INTEGER NOT NULL,
    received_date TEXT NOT NULL,
    expiry_date   TEXT,
    cost_price    REAL NOT NULL
);
""")

# Add shelf-life column to products (only if it does not exist yet)
cols = [r[1] for r in cur.execute("PRAGMA table_info(products)")]
if "shelf_life_days" not in cols:
    cur.execute("ALTER TABLE products ADD COLUMN shelf_life_days INTEGER")
cur.execute("UPDATE products SET shelf_life_days = NULL")

cur.execute("INSERT INTO settings VALUES ('as_of_date', ?)", (as_of.isoformat(),))

products = pd.read_sql("SELECT stock_code, unit_price FROM products", conn)

# 10 products get a simulated shelf life of 30-90 days
perishable = rng.choice(products["stock_code"], size=10, replace=False)
for code in perishable:
    cur.execute(
        "UPDATE products SET shelf_life_days = ? WHERE stock_code = ?",
        (int(rng.integers(30, 91)), code),
    )

# 3 simulated suppliers
suppliers = [("Metro Wholesale", 2), ("QuickStock Traders", 4), ("Prime Supply Co", 7)]
cur.executemany("INSERT INTO suppliers (name, lead_time_days) VALUES (?, ?)", suppliers)

# Each supplier quotes 45-70% of the selling price
price_rows = []
for _, p in products.iterrows():
    for sid in (1, 2, 3):
        cost = round(p["unit_price"] * rng.uniform(0.45, 0.70), 2)
        price_rows.append((sid, p["stock_code"], cost))
cur.executemany("INSERT INTO supplier_prices VALUES (?, ?, ?)", price_rows)
avg_cost = pd.DataFrame(price_rows, columns=["s", "code", "cost"]).groupby("code")["cost"].mean()

# Average daily demand over the last 28 days
start = (as_of - timedelta(days=28)).isoformat()
avg = pd.read_sql(
    f"SELECT stock_code, SUM(quantity)/28.0 AS avg_daily FROM sales "
    f"WHERE sale_date >= '{start}' GROUP BY stock_code",
    conn,
).set_index("stock_code")["avg_daily"]

shelf = dict(cur.execute("SELECT stock_code, shelf_life_days FROM products").fetchall())

# Stock batches: each product holds 3-20 days of stock, split into 1-2 batches
batch_rows = []
for code in products["stock_code"]:
    daily = float(avg.get(code, 5.0))
    total = max(5, int(daily * rng.uniform(3, 20)))
    n = int(rng.integers(1, 3))
    parts = np.array_split(np.arange(total), n)
    for part in parts:
        qty = len(part)
        if qty == 0:
            continue
        received = as_of - timedelta(days=int(rng.integers(1, 45)))
        expiry = None
        if shelf[code] is not None:
            expiry = (received + timedelta(days=shelf[code])).isoformat()
        batch_rows.append((code, qty, received.isoformat(), expiry, round(float(avg_cost[code]), 2)))
cur.executemany(
    "INSERT INTO stock_batches (stock_code, quantity, received_date, expiry_date, cost_price) "
    "VALUES (?, ?, ?, ?, ?)",
    batch_rows,
)
conn.commit()

# Quick checks
print("Suppliers:", cur.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0])
print("Supplier prices:", cur.execute("SELECT COUNT(*) FROM supplier_prices").fetchone()[0])
print("Stock batches:", cur.execute("SELECT COUNT(*) FROM stock_batches").fetchone()[0])
print("Products with shelf life:", cur.execute("SELECT COUNT(*) FROM products WHERE shelf_life_days IS NOT NULL").fetchone()[0])
print("Batches already expired:", cur.execute(
    "SELECT COUNT(*) FROM stock_batches WHERE expiry_date < ?", (as_of.isoformat(),)).fetchone()[0])
print("Batches expiring in next 14 days:", cur.execute(
    "SELECT COUNT(*) FROM stock_batches WHERE expiry_date BETWEEN ? AND ?",
    (as_of.isoformat(), (as_of + timedelta(days=14)).isoformat())).fetchone()[0])
conn.close()
print("\nSimulated data added to data/inventory.db")