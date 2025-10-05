import os
import math
import datetime as dt
import numpy as np
import pandas as pd
import requests
import joblib
from sklearn.ensemble import RandomForestRegressor

# -------------------------
# DATA FETCH (NASA POWER)
# -------------------------
def fetch_nasa_power(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point?"
        f"latitude={lat}&longitude={lon}&start={start}&end={end}"
        f"&parameters=T2M,RH2M,WS10M,PRECTOTCORR&community=ag&format=JSON"
    )
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data["properties"]["parameter"])
    df.index = pd.to_datetime(df.index)
    df.rename(
        columns={
            "T2M": "Temp",
            "RH2M": "Humidity",
            "WS10M": "Wind",
            "PRECTOTCORR": "Precip",
        },
        inplace=True,
    )
    df = df.reset_index().rename(columns={"index": "Date"})
    return df

# -------------------------
# FEATURE ENGINEERING
# -------------------------
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["doy"] = out["Date"].dt.dayofyear
    out["sin_doy"] = np.sin(2 * np.pi * out["doy"] / 366)
    out["cos_doy"] = np.cos(2 * np.pi * out["doy"] / 366)
    for c in ["Temp", "Humidity", "Wind", "Precip"]:
        for lag in [1, 7, 14]:
            out[f"{c}_lag{lag}"] = out[c].shift(lag)
        out[f"{c}_roll7"] = out[c].rolling(7).mean()
    return out.dropna().reset_index(drop=True)

# -------------------------
# TRAIN / CACHE MODELS
# -------------------------
def cache_path(lat: float, lon: float, start: str, end: str) -> str:
    os.makedirs("model_cache", exist_ok=True)
    key = f"{round(lat,2)}_{round(lon,2)}_{start}_{end}".replace(".", "p").replace("-", "")
    return os.path.join("model_cache", f"{key}.joblib")

def train_or_load_models(lat: float, lon: float, start: str, end: str):
    cp = cache_path(lat, lon, start, end)
    if os.path.exists(cp):
        return joblib.load(cp)

    df = fetch_nasa_power(lat, lon, start, end)
    df_fe = add_features(df)
    feats = [c for c in df_fe.columns if c not in ["Date", "Temp", "Humidity", "Wind", "Precip"]]
    targets = ["Temp", "Humidity", "Wind", "Precip"]

    models = {}
    for t in targets:
        rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(df_fe[feats], df_fe[t])
        models[t] = rf

    payload = {"df": df, "models": models, "feats": feats}
    joblib.dump(payload, cp)
    return payload

# -------------------------
# FORECAST
# -------------------------
def forecast(payload: dict, target_date: dt.date) -> pd.DataFrame:
    df = payload["df"].copy().sort_values("Date").reset_index(drop=True)
    models = payload["models"]
    feats = payload["feats"]

    last_date = df["Date"].iloc[-1]
    horizon_days = (pd.Timestamp(target_date) - last_date).days
    if horizon_days <= 0:
        return df

    max_horizon = 365 * 6
    horizon_days = min(horizon_days, max_horizon)

    # iterative day-ahead prediction
    for _ in range(horizon_days):
        next_date = df["Date"].iloc[-1] + pd.Timedelta(days=1)
        tmp = pd.concat([df, pd.DataFrame({"Date": [next_date]})], ignore_index=True)
        tmp_fe = add_features(tmp)
        X = tmp_fe.iloc[[-1]][feats]
        preds = {t: float(models[t].predict(X)[0]) for t in models}
        new_row = {
            "Date": next_date,
            "Temp": preds["Temp"],
            "Humidity": preds["Humidity"],
            "Wind": preds["Wind"],
            "Precip": max(preds["Precip"], 0.0),
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    return df

# -------------------------
# IRRIGATION (Hargreaves-ish)
# -------------------------
def extraterrestrial_radiation(latitude: float, doy: int) -> float:
    phi = math.radians(latitude)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    delta = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)
    omega_s = math.acos(-math.tan(phi) * math.tan(delta))
    Gsc = 0.0820
    return (24 * 60 / math.pi) * Gsc * dr * (
        omega_s * math.sin(phi) * math.sin(delta)
        + math.cos(phi) * math.cos(delta) * math.sin(omega_s)
    )

def estimate_trange(temp: float, humidity: float, wind: float) -> float:
    tr = 12 + (50 - humidity) * 0.03 + wind * 0.6
    return float(np.clip(tr, 6, 16))

def et0(temp: float, humidity: float, wind: float, lat: float, date: dt.date) -> float:
    doy = date.timetuple().tm_yday
    tr = estimate_trange(temp, humidity, wind)
    Ra = extraterrestrial_radiation(lat, doy)
    return 0.0023 * (temp + 17.8) * math.sqrt(tr) * Ra

def irrigation(temp: float, humidity: float, wind: float, precip: float,
               lat: float, date: dt.date, kc: float, soil_buffer: float = 2.0,
               eff_rain_factor: float = 0.8):
    et0_val = et0(temp, humidity, wind, lat, date)
    etc = kc * et0_val
    peff = eff_rain_factor * precip
    net = max(0.0, etc - peff - soil_buffer)
    return net, et0_val, etc, peff

# -------------------------
# ADVISORY
# -------------------------
def advisory(pred: dict, irr_mm: float, etc: float, et0_val: float) -> dict:
    temp = pred["Temp"]; hum = pred["Humidity"]; wind = pred["Wind"]; precip = pred["Precip"]
    recs = {}
    if precip > 5:
        recs["irrigation"] = f"💧 Skip irrigation — rainfall {precip:.1f} mm."
    elif irr_mm > 5:
        recs["irrigation"] = f"🚜 Irrigate {irr_mm:.1f} mm (ETc={etc:.2f})."
    else:
        recs["irrigation"] = "✅ No irrigation needed."

    if hum > 85 and 18 < temp < 28:
        recs["pest"] = "🐛 High fungal risk (blight/mildew) — consider fungicide."
    elif hum < 40:
        recs["pest"] = "🪳 Low pest pressure — dry conditions."
    else:
        recs["pest"] = "⚠️ Moderate pest risk — scout fields."

    if precip > 3 or hum > 90:
        recs["field"] = "❌ Too wet for tractor."
    elif wind > 7:
        recs["field"] = "🌬️ Windy — avoid spraying/seeding."
    else:
        recs["field"] = "✅ Good window for field work."

    if temp < 2:
        recs["frost"] = "❄️ Frost risk — protect seedlings."
    elif temp < 6:
        recs["frost"] = "⚠️ Mild cold risk."
    else:
        recs["frost"] = "🌡️ No frost risk."

    if 50 < hum < 70 and wind < 5 and precip < 0.5:
        recs["spray"] = "💉 Excellent spray conditions."
    else:
        recs["spray"] = "🚫 Suboptimal for spraying."

    return recs
