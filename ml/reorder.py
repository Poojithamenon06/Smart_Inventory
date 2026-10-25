import os
import math
import sqlite3
import numpy as np
import pandas as pd
from forecast import load_history, forecast_many

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "inventory.db")

Z = 1.65         # 95% service level
REVIEW_DAYS = 7  # days of demand each order should cover after delivery


def build_recommendations():
    conn = sqlite3.connect(DB)
    as_of = conn.execute("SELECT value FROM settings WHERE key = 'as_of_date'").fetchone()[0]

    products = pd.read_sql("SELECT stock_code, description FROM products", conn)
    stock = pd.read_sql(
        "SELECT stock_code, SUM(quantity) AS current_stock FROM stock_batches "
        "WHERE expiry_date IS NULL OR expiry_date >= ? GROUP BY stock_code",
        conn, params=(as_of,),
    )
    best = pd.read_sql(
        "SELECT sp.stock_code, s.name AS supplier, s.lead_time_days, sp.cost_price "
        "FROM supplier_prices sp JOIN suppliers s ON s.id = sp.supplier_id",
        conn,
    )
    last_cost = pd.read_sql(
        "SELECT stock_code, cost_price AS last_cost FROM stock_batches "
        "WHERE id IN (SELECT MAX(id) FROM stock_batches GROUP BY stock_code)",
        conn,
    )
    conn.close()

    # Cheapest supplier for each product
    best = best.sort_values("cost_price").groupby("stock_code").first().reset_index()

    df = (
        products.merge(stock, on="stock_code", how="left")
        .merge(best, on="stock_code", how="left")
        .merge(last_cost, on="stock_code", how="left")
    )
    df["supplier"] = df["supplier"].fillna("Not set")
    df["lead_time_days"] = df["lead_time_days"].fillna(3)
    df["cost_price"] = df["cost_price"].fillna(df["last_cost"])
    df = df.dropna(subset=["cost_price"])  # no quote and no stock received yet
    df["current_stock"] = df["current_stock"].fillna(0)

    history, last_date = load_history()
    fc_all = forecast_many(history, last_date, int(df["lead_time_days"].max()) + REVIEW_DAYS)
    rows = []
    for _, r in df.iterrows():
        hist = history[r["stock_code"]]
        L = int(r["lead_time_days"])
        fc = pd.Series(fc_all[r["stock_code"]][: L + REVIEW_DAYS])

        demand_lt = fc.iloc[:L].sum()
        demand_review = fc.iloc[L:].sum()
        std = float(np.std(hist[-28:], ddof=1)) if len(hist) > 1 else 0.0
        safety = Z * std * math.sqrt(L)

        reorder_point = demand_lt + safety
        target = demand_lt + demand_review + safety
        stock_now = float(r["current_stock"])
        needs_order = stock_now <= reorder_point
        order_qty = max(0, math.ceil(target - stock_now)) if needs_order else 0

        rows.append({
            "stock_code": r["stock_code"],
            "description": r["description"],
            "current_stock": int(stock_now),
            "avg_daily_forecast": round(fc.mean(), 1),
            "days_of_cover": round(stock_now / max(fc.mean(), 0.1), 1),
            "safety_stock": round(safety),
            "reorder_point": round(reorder_point),
            "needs_order": needs_order,
            "order_qty": order_qty,
            "supplier": r["supplier"],
            "lead_time_days": L,
            "cost_price": r["cost_price"],
            "order_cost": round(order_qty * r["cost_price"], 2),
        })
    return pd.DataFrame(rows)

def _state():
    conn = sqlite3.connect(DB)
    s = conn.execute(
        "SELECT (SELECT MAX(id) FROM sales), (SELECT COUNT(*) FROM products), "
        "(SELECT COUNT(*) FROM stock_batches), (SELECT COALESCE(SUM(quantity), 0) FROM stock_batches)"
    ).fetchone()
    conn.close()
    return s


_cache = {"state": None, "df": None}


def get_recommendations():
    s = _state()
    if _cache["state"] != s:
        _cache["df"] = build_recommendations()
        _cache["state"] = s
    return _cache["df"].copy()

if __name__ == "__main__":
    rec = build_recommendations()
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)

    print("Products needing an order:", int(rec["needs_order"].sum()), "of", len(rec))
    print("Total order cost:", round(rec["order_cost"].sum(), 2))
    print("\nMost urgent (lowest days of cover):")
    cols = ["description", "current_stock", "days_of_cover", "reorder_point", "order_qty", "supplier"]
    top = rec.sort_values("days_of_cover").head(10).copy()
    top["description"] = top["description"].str.strip().str[:28]
    print(top[cols].to_string(index=False))

    rec.to_csv(os.path.join(ROOT, "data", "processed", "reorder_recommendations.csv"), index=False)
    print("\nSaved to data/processed/reorder_recommendations.csv")