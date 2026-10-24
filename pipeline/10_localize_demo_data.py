import shutil
import sqlite3
import pandas as pd

RATE = 130         # approximate GBP -> INR rate, fixed for the demo
SHIFT_DAYS = 5432  # 776 weeks: keeps weekdays, moves 2011-12-09 to 2026-10-23

conn = sqlite3.connect("data/inventory.db")
done = conn.execute("SELECT value FROM settings WHERE key = 'demo_localized'").fetchone()
conn.close()
if done:
    print("Already converted. Nothing to do.")
    raise SystemExit

shutil.copy("data/inventory.db", "data/inventory_backup_before_inr.db")

conn = sqlite3.connect("data/inventory.db")
conn.executescript(f"""
UPDATE products SET unit_price = MAX(1, ROUND(unit_price * {RATE}));
UPDATE sales SET
    unit_price = MAX(1, ROUND(unit_price * {RATE})),
    sale_date = date(sale_date, '+{SHIFT_DAYS} days'),
    sale_datetime = datetime(sale_datetime, '+{SHIFT_DAYS} days');
UPDATE sales SET
    sale_date = date(sale_date, '-1 day'),
    sale_datetime = datetime(sale_datetime, '-1 day')
WHERE invoice = 'LIVE';
UPDATE supplier_prices SET cost_price = ROUND(cost_price * {RATE}, 2);
UPDATE stock_batches SET
    cost_price = ROUND(cost_price * {RATE}, 2),
    received_date = date(received_date, '+{SHIFT_DAYS} days'),
    expiry_date = date(expiry_date, '+{SHIFT_DAYS} days');
UPDATE settings SET value = date(value, '+{SHIFT_DAYS - 1} days') WHERE key = 'as_of_date';
INSERT INTO settings VALUES ('demo_localized', 'INR at {RATE}, dates shifted {SHIFT_DAYS} days');
""")
conn.commit()

print("Latest sale date:", conn.execute("SELECT MAX(sale_date) FROM sales").fetchone()[0])
print("Simulated today:", conn.execute("SELECT value FROM settings WHERE key = 'as_of_date'").fetchone()[0])
print("Sample prices (Rs):", conn.execute("SELECT description, unit_price FROM products LIMIT 3").fetchall())
conn.close()

# The forecasting history must move by the same amount
d = pd.read_csv("data/processed/daily_sales.csv", dtype={"StockCode": str}, parse_dates=["Date"])
d["Date"] = d["Date"] + pd.Timedelta(days=SHIFT_DAYS)
d.to_csv("data/processed/daily_sales.csv", index=False)
print("Forecast history last date:", d["Date"].max().date())