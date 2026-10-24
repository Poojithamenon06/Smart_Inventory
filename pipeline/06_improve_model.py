import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

df = pd.read_csv(
    "data/processed/features.csv",
    dtype={"StockCode": str},
    parse_dates=["Date"],
)

# Scale-free features: everything is divided by the product's 28-day average
scale = df["roll_mean_28"] + 1
X = pd.DataFrame({
    "lag_1": df["lag_1"] / scale,
    "lag_2": df["lag_2"] / scale,
    "lag_7": df["lag_7"] / scale,
    "lag_14": df["lag_14"] / scale,
    "roll_mean_7": df["roll_mean_7"] / scale,
    "roll_std_7": df["roll_std_7"] / scale,
    "log_scale": np.log1p(scale),
    "dayofweek": df["dayofweek"],
})
y = df["Quantity"] / scale

dates = sorted(df["Date"].unique())
cutoff = dates[-60]
train_idx = df["Date"] < cutoff
test_idx = ~train_idx

model = HistGradientBoostingRegressor(
    loss="absolute_error", max_iter=300, learning_rate=0.05, max_depth=4
)
model.fit(X[train_idx], y[train_idx])
pred = np.clip(model.predict(X[test_idx]), 0, None) * scale[test_idx]

actual = df.loc[test_idx, "Quantity"]
print("Average daily quantity in test:", round(actual.mean(), 1))
print("\nMAE (lower is better)")
print("Baseline last 7-day average :", round(mean_absolute_error(actual, df.loc[test_idx, "roll_mean_7"]), 2))
print("Baseline last 28-day average:", round(mean_absolute_error(actual, df.loc[test_idx, "roll_mean_28"]), 2))
print("Baseline same weekday last wk:", round(mean_absolute_error(actual, df.loc[test_idx, "lag_7"]), 2))
print("Improved model              :", round(mean_absolute_error(actual, pred), 2))