import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

df = pd.read_csv(
    "data/processed/daily_sales.csv",
    dtype={"StockCode": str},
    parse_dates=["Date"],
)
df = df.sort_values(["StockCode", "Date"]).reset_index(drop=True)

# Lag and rolling features (shift(1) so we never use the day's own sales)
g = df.groupby("StockCode")["Quantity"]
for lag in [1, 2, 7, 14]:
    df[f"lag_{lag}"] = g.shift(lag)
df["roll_mean_7"] = g.transform(lambda s: s.shift(1).rolling(7).mean())
df["roll_mean_28"] = g.transform(lambda s: s.shift(1).rolling(28).mean())
df["roll_std_7"] = g.transform(lambda s: s.shift(1).rolling(7).std())

# Calendar features
df["dayofweek"] = df["Date"].dt.dayofweek
df["month"] = df["Date"].dt.month
df["weekofyear"] = df["Date"].dt.isocalendar().week.astype(int)
df["product"] = df["StockCode"].astype("category")

df = df.dropna().reset_index(drop=True)

features = [
    "lag_1", "lag_2", "lag_7", "lag_14",
    "roll_mean_7", "roll_mean_28", "roll_std_7",
    "dayofweek", "month", "weekofyear", "product",
]

# Time-based split: last 60 open days are the test set
dates = sorted(df["Date"].unique())
cutoff = dates[-60]
train = df[df["Date"] < cutoff]
test = df[df["Date"] >= cutoff]
print("Train rows:", len(train), "| Test rows:", len(test))
print("Test period:", test["Date"].min().date(), "to", test["Date"].max().date())

# Baseline: predict the last 7-day average
baseline_mae = mean_absolute_error(test["Quantity"], test["roll_mean_7"])

# LightGBM model
model = HistGradientBoostingRegressor(
    max_iter=500, learning_rate=0.05, categorical_features="from_dtype"
)
model.fit(train[features], train["Quantity"])
pred = np.clip(model.predict(test[features]), 0, None)
model_mae = mean_absolute_error(test["Quantity"], pred)

print("\nAverage daily quantity in test:", round(test["Quantity"].mean(), 1))
print("Baseline MAE:", round(baseline_mae, 2))
print("LightGBM MAE:", round(model_mae, 2))
print("Improvement over baseline:", round((1 - model_mae / baseline_mae) * 100, 1), "%")

# Save for the next steps
df.to_csv("data/processed/features.csv", index=False)
print("\nSaved to data/processed/features.csv")