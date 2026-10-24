import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

df = pd.read_csv(
    "data/processed/features.csv",
    dtype={"StockCode": str},
    parse_dates=["Date"],
)

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

model = HistGradientBoostingRegressor(
    loss="absolute_error", max_iter=300, learning_rate=0.05, max_depth=4
)
model.fit(X, y)

joblib.dump({"model": model, "features": list(X.columns)}, "ml/demand_model.joblib")
print("Model saved to ml/demand_model.joblib")