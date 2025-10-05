import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib

# === PATHS ===
csv_path = "nasa_power_data.csv"
output_dir = "model"
os.makedirs(output_dir, exist_ok=True)

# === LOAD DATA ===
df = pd.read_csv(csv_path)
df.columns = ["Date", "Temp", "Humidity", "Wind", "Precip"]
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").reset_index(drop=True)

# === FEATURE ENGINEERING ===
def add_features(df):
    out = df.copy()
    out["doy"] = out["Date"].dt.dayofyear
    out["sin_doy"] = np.sin(2 * np.pi * out["doy"] / 366)
    out["cos_doy"] = np.cos(2 * np.pi * out["doy"] / 366)
    for col in ["Temp", "Humidity", "Wind", "Precip"]:
        for lag in [1, 7, 14]:
            out[f"{col}_lag{lag}"] = out[col].shift(lag)
        out[f"{col}_roll7"] = out[col].rolling(7).mean()
    return out.dropna().reset_index(drop=True)

data = add_features(df)
targets = ["Temp", "Humidity", "Wind", "Precip"]
feats = [c for c in data.columns if c not in ["Date"] + targets]

# === TRAIN & SAVE MODELS ===
for t in targets:
    print(f"Training {t} model...")
    rf = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(data[feats], data[t])
    joblib.dump(rf, os.path.join(output_dir, f"{t}_model.pkl"))

print("✅ All models trained and saved to /model folder.")
