import os
import sqlite3

import joblib
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "inventory.db")

_bundle = joblib.load(os.path.join(HERE, "demand_model.joblib"))
MODEL = _bundle["model"]
FEATURES = _bundle["features"]
MIN_HISTORY = 28  # below this the model has too little data, so a plain average is used


def load_history():
    """Daily quantity per product on every shop-open day, read from the live sales table."""
    conn = sqlite3.connect(DB)
    df = pd.read_sql(
        "SELECT sale_date AS Date, stock_code AS StockCode, SUM(quantity) AS Quantity "
        "FROM sales GROUP BY sale_date, stock_code",
        conn, parse_dates=["Date"],
    )
    codes = pd.read_sql("SELECT stock_code FROM products", conn)["stock_code"]
    conn.close()

    days = sorted(df["Date"].unique())
    table = df.pivot_table(index="Date", columns="StockCode", values="Quantity", aggfunc="sum")
    table = table.reindex(days).fillna(0)

    history = {}
    for code in codes:
        if code in table.columns:
            s = table[code]
            first = s[s > 0].index.min()  # start counting at the product's first sale
            history[code] = s[s.index >= first].tolist() if pd.notna(first) else []
        else:
            history[code] = []
    return history, pd.Timestamp(days[-1])


def next_open_days(last_date, n):
    days = []
    d = pd.Timestamp(last_date)
    while len(days) < n:
        d += pd.Timedelta(days=1)
        if d.dayofweek != 5:  # the shop is closed on Saturdays
            days.append(d)
    return days


def forecast_product(history, last_date, horizon=7):
    h = list(history)
    days = next_open_days(last_date, horizon)

    # New product: too little history for the model, so use its average daily sales
    if len(h) < MIN_HISTORY:
        level = float(np.mean(h)) if h else 0.0
        return pd.DataFrame([(d.date(), level) for d in days], columns=["date", "forecast"])

    rows = []
    for d in days:
        scale = np.mean(h[-28:]) + 1
        x = {
            "lag_1": h[-1] / scale,
            "lag_2": h[-2] / scale,
            "lag_7": h[-7] / scale,
            "lag_14": h[-14] / scale,
            "roll_mean_7": np.mean(h[-7:]) / scale,
            "roll_std_7": np.std(h[-7:], ddof=1) / scale,
            "log_scale": np.log1p(scale),
            "dayofweek": d.dayofweek,
        }
        X = pd.DataFrame([x])[FEATURES]
        pred = max(0.0, float(MODEL.predict(X)[0]) * scale)
        h.append(pred)
        rows.append((d.date(), pred))
    return pd.DataFrame(rows, columns=["date", "forecast"])

def forecast_many(history, last_date, horizon):
    """Forecast `horizon` open days for every product at once (one model call per day)."""
    days = next_open_days(last_date, horizon)
    h = {c: list(v) for c, v in history.items()}
    out = {c: [] for c in h}
    model_codes = [c for c in h if len(h[c]) >= MIN_HISTORY]
    for c in h:
        if c not in model_codes:  # too little history: plain average
            level = float(np.mean(h[c])) if h[c] else 0.0
            out[c] = [level] * horizon
    if not model_codes:
        return out
    for d in days:
        rows, scales = [], []
        for c in model_codes:
            s = h[c]
            scale = np.mean(s[-28:]) + 1
            scales.append(scale)
            rows.append({
                "lag_1": s[-1] / scale, "lag_2": s[-2] / scale,
                "lag_7": s[-7] / scale, "lag_14": s[-14] / scale,
                "roll_mean_7": np.mean(s[-7:]) / scale,
                "roll_std_7": np.std(s[-7:], ddof=1) / scale,
                "log_scale": np.log1p(scale), "dayofweek": d.dayofweek,
            })
        preds = np.clip(MODEL.predict(pd.DataFrame(rows)[FEATURES]), 0, None) * np.array(scales)
        for c, p in zip(model_codes, preds):
            h[c].append(float(p))
            out[c].append(float(p))
    return out
if __name__ == "__main__":
    history, last_date = load_history()
    code = "85123A"  # WHITE HANGING HEART T-LIGHT HOLDER
    print("Last data date:", last_date.date())
    print("Last 7 actual open days:", history[code][-7:])
    fc = forecast_product(history[code], last_date, horizon=7)
    print(fc.round(1))
    print("Total forecast for next 7 open days:", round(fc["forecast"].sum(), 1))