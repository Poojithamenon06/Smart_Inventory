import os
import shutil
import sqlite3
import sys

sys.path.append("backend")  # so we can reuse the password hashing from auth.py

os.makedirs("demo", exist_ok=True)
shutil.copy("data/inventory.db", "demo/inventory.db")

conn = sqlite3.connect("demo/inventory.db")
conn.execute("DELETE FROM users")                       # remove personal accounts
conn.execute("DELETE FROM sales WHERE invoice = 'LIVE'")  # remove test sales
import auth

conn.execute(
    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, datetime('now'))",
    ("demo", auth.hash_password("demo1234")),
)
conn.commit()
conn.execute("VACUUM")
conn.close()

print(f"demo/inventory.db created: {os.path.getsize('demo/inventory.db') / 1_000_000:.1f} MB")
print("Demo login: demo / demo1234")