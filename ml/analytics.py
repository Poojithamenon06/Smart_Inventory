import os
import sqlite3
import pandas as pd
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "inventory.db")

COST_SUBQUERY = """
    (SELECT stock_code, AVG(cost_price) AS avg_cost
     FROM supplier_prices GROUP BY stock_code)
"""


def get_as_of(conn):
    return conn.execute("SELECT value FROM settings WHERE key = 'as_of_date'").fetchone()[0]


def expiry_alerts(days_ahead=30):
    """Batches expiring soon, with an estimate of units that will not sell in time."""
    conn = sqlite3.connect(DB)
    as_of = get_as_of(conn)
    start = (date.fromisoformat(as_of) - timedelta(days=28)).isoformat()

    df = pd.read_sql(
        """
        SELECT b.id AS batch_id, b.stock_code, p.description, b.quantity,
               b.expiry_date, b.cost_price, COALESCE(d.avg_daily, 0) AS avg_daily
        FROM stock_batches b
        JOIN products p ON p.stock_code = b.stock_code
        LEFT JOIN (
            SELECT stock_code, SUM(quantity) / 28.0 AS avg_daily
            FROM sales WHERE sale_date >= ? GROUP BY stock_code
        ) d ON d.stock_code = b.stock_code
        WHERE b.expiry_date IS NOT NULL
        """,
        conn, params=(start,),
    )
    conn.close()

    df["days_left"] = (pd.to_datetime(df["expiry_date"]) - pd.Timestamp(as_of)).dt.days
    df = df[df["days_left"] <= days_ahead].copy()

    def status(d):
        if d < 0:
            return "expired"
        if d <= 7:
            return "critical"
        if d <= 14:
            return "warning"
        return "watch"

    df["status"] = df["days_left"].apply(status)

    # Simplification: each batch is compared against the product's average daily demand
    expected_sales = df["avg_daily"] * df["days_left"].clip(lower=0)
    df["units_at_risk"] = (df["quantity"] - expected_sales).clip(lower=0).round().astype(int)
    df["value_at_risk"] = (df["units_at_risk"] * df["cost_price"]).round(2)

    df["description"] = df["description"].str.strip()
    return df.sort_values("days_left")[
        ["batch_id", "stock_code", "description", "quantity", "expiry_date",
         "days_left", "status", "units_at_risk", "value_at_risk"]
    ]


def daily_summary(days=7):
    """Revenue, cost, and profit for the most recent sales days."""
    conn = sqlite3.connect(DB)
    df = pd.read_sql(
        f"""
        SELECT s.sale_date,
               SUM(s.quantity) AS units,
               SUM(s.quantity * s.unit_price) AS revenue,
               SUM(s.quantity * c.avg_cost) AS cost
        FROM sales s JOIN {COST_SUBQUERY} c ON c.stock_code = s.stock_code
        GROUP BY s.sale_date
        ORDER BY s.sale_date DESC LIMIT ?
        """,
        conn, params=(days,),
    )
    conn.close()
    df["profit"] = df["revenue"] - df["cost"]
    df["margin_pct"] = (df["profit"] / df["revenue"] * 100).round(1)
    for col in ["revenue", "cost", "profit"]:
        df[col] = df[col].round(2)
    return df.sort_values("sale_date")


def top_products_by_profit(sale_date, n=5):
    conn = sqlite3.connect(DB)
    df = pd.read_sql(
        f"""
        SELECT p.description,
               SUM(s.quantity) AS units,
               ROUND(SUM(s.quantity * (s.unit_price - c.avg_cost)), 2) AS profit
        FROM sales s
        JOIN products p ON p.stock_code = s.stock_code
        JOIN {COST_SUBQUERY} c ON c.stock_code = s.stock_code
        WHERE s.sale_date = ?
        GROUP BY s.stock_code ORDER BY profit DESC LIMIT ?
        """,
        conn, params=(sale_date, n),
    )
    conn.close()
    df["description"] = df["description"].str.strip()
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)

    alerts = expiry_alerts(30)
    print("Batches expiring within 30 days:", len(alerts))
    print("Total value at risk:", round(alerts["value_at_risk"].sum(), 2))
    alerts_show = alerts.copy()
    alerts_show["description"] = alerts_show["description"].str[:28]
    print(alerts_show.head(10).to_string(index=False))

    summary = daily_summary(7)
    print("\nDaily profit summary (last 7 sales days):")
    print(summary.to_string(index=False))

    last_day = summary["sale_date"].iloc[-1]
    print(f"\nTop 5 products by profit on {last_day}:")
    print(top_products_by_profit(last_day).to_string(index=False))