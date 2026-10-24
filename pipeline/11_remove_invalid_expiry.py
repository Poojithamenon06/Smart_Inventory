import sqlite3

conn = sqlite3.connect("data/inventory.db")
cur = conn.cursor()

rows = cur.execute(
    "SELECT description FROM products WHERE shelf_life_days IS NOT NULL"
).fetchall()
print("Products that had an invalid shelf life (now removed):")
for r in rows:
    print(" -", r[0].strip())

cur.execute("UPDATE products SET shelf_life_days = NULL")
cur.execute("UPDATE stock_batches SET expiry_date = NULL")
conn.commit()

print("\nBatches with an expiry date now:",
      cur.execute("SELECT COUNT(*) FROM stock_batches WHERE expiry_date IS NOT NULL").fetchone()[0])
conn.close()