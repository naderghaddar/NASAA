import os
import math
import datetime as dt
import numpy as np
import pandas as pd
import joblib
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# ---------------------------- SETTINGS ----------------------------
st.set_page_config(page_title="Irrigation Planner", layout="centered")
st.title("🌾 Smart Irrigation Planner")

st.markdown(
    """
This tool predicts weather and irrigation needs up to **6 years ahead**  
using trained RandomForest models on NASA POWER historical data.  
Enter your latitude, longitude, and target date — then click **Predict**.
"""
)

# ---------------------------- PATHS ----------------------------
data_path = os.path.join(os.path.dirname(__file__), "nasa_power_data.csv")
model_dir = os.path.join(os.path.dirname(__file__), "model")
targets = ["Temp", "Humidity", "Wind", "Precip"]

# ---------------------------- LOAD DATA ----------------------------
if not os.path.exists(data_path):
    st.error(f"❌ Dataset not found at: {data_path}")
    st.stop()

df = pd.read_csv(data_path)
df.columns = ["Date", "Temp", "Humidity", "Wind", "Precip"]
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").reset_index(drop=True)

# ---------------------------- LOAD MODELS ----------------------------
if not all(os.path.exists(os.path.join(model_dir, f"{t}_model.pkl")) for t in targets):
    st.error("❌ Model files not found. Please run `train_model.py` first to generate them.")
    st.stop()

models = {t: joblib.load(os.path.join(model_dir, f"{t}_model.pkl")) for t in targets}
st.success("✅ Models loaded successfully.")

# ---------------------------- INPUTS ----------------------------
st.sidebar.header("Settings")
lat = st.sidebar.number_input("Latitude (°)", -60.0, 60.0, 45.0, step=0.1)
lon = st.sidebar.number_input("Longitude (°)", -180.0, 180.0, -73.0, step=0.1)
target_date = st.sidebar.date_input("Date to predict", value=dt.date.today() + dt.timedelta(days=7))
kc = st.sidebar.slider("Crop coefficient (Kc)", 0.6, 1.3, 1.15, 0.05)
soil_buffer = st.sidebar.slider("Soil moisture buffer (mm)", 0, 10, 2)
eff_rain_factor = 0.8

# ---------------------------- FEATURE ENGINEERING ----------------------------
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

# ---------------------------- FORECAST ----------------------------
def forecast(df, models, target_date):
    hist = df.copy()
    hist = hist.sort_values("Date").reset_index(drop=True)
    feats = [
        c for c in add_features(df).columns
        if c not in ["Date", "Temp", "Humidity", "Wind", "Precip"]
    ]

    last_date = hist["Date"].iloc[-1]
    horizon_days = (pd.Timestamp(target_date) - last_date).days

    if horizon_days <= 0:
        st.warning("⚠️ The chosen date is before or within the dataset range. Try a future date.")
        return hist

    max_horizon = 365 * 6  # 6 years
    if horizon_days > max_horizon:
        st.warning("⚠️ Limiting forecast to 6 years (~2190 days).")
        horizon_days = max_horizon

    for _ in range(horizon_days):
        next_date = hist["Date"].iloc[-1] + pd.Timedelta(days=1)
        tmp = pd.concat([hist, pd.DataFrame({"Date": [next_date]})], ignore_index=True)
        tmp = add_features(tmp)
        feat = tmp.iloc[[-1]][feats]
        preds = {t: models[t].predict(feat)[0] for t in targets}
        new_row = pd.DataFrame([{
            "Date": next_date,
            "Temp": preds["Temp"],
            "Humidity": preds["Humidity"],
            "Wind": preds["Wind"],
            "Precip": max(preds["Precip"], 0)
        }])
        hist = pd.concat([hist, new_row], ignore_index=True)

    return hist

# ---------------------------- IRRIGATION CALCULATION ----------------------------
def extraterrestrial_radiation(latitude, doy):
    phi = math.radians(latitude)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    delta = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)
    omega_s = math.acos(-math.tan(phi) * math.tan(delta))
    Gsc = 0.0820
    return (24 * 60 / math.pi) * Gsc * dr * (
        omega_s * math.sin(phi) * math.sin(delta)
        + math.cos(phi) * math.cos(delta) * math.sin(omega_s)
    )

def estimate_trange(temp, humidity, wind):
    tr = 12 + (50 - humidity) * 0.03 + wind * 0.6
    return float(np.clip(tr, 6, 16))

def et0(temp, humidity, wind, lat, date):
    doy = date.timetuple().tm_yday
    tr = estimate_trange(temp, humidity, wind)
    Ra = extraterrestrial_radiation(lat, doy)
    return 0.0023 * (temp + 17.8) * math.sqrt(tr) * Ra

def irrigation(temp, humidity, wind, precip, lat, date, kc):
    et0_val = et0(temp, humidity, wind, lat, date)
    etc = kc * et0_val
    peff = eff_rain_factor * precip
    net = max(0, etc - peff - soil_buffer)
    return net, et0_val, etc, peff

# ---------------------------- PREDICT BUTTON ----------------------------
if st.button("🌤️ Predict"):
    with st.spinner("Generating long-term forecast..."):
        future = forecast(df, models, target_date)
        pred_row = future[future["Date"] == pd.Timestamp(target_date)].iloc[0]

        irr, et0_val, etc, peff = irrigation(
            pred_row["Temp"], pred_row["Humidity"], pred_row["Wind"],
            pred_row["Precip"], lat, target_date, kc
        )
        liters = irr * 10000

    st.success(f"✅ Forecast for {target_date.isoformat()}:")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🌡️ Temperature (°C)", f"{pred_row['Temp']:.1f}")
        st.metric("💧 Humidity (%)", f"{pred_row['Humidity']:.0f}")
        st.metric("🌬️ Wind (m/s)", f"{pred_row['Wind']:.2f}")
        st.metric("🌦️ Precipitation (mm)", f"{pred_row['Precip']:.2f}")

    with col2:
        st.metric("Irrigation (mm)", f"{irr:.2f}")
        st.metric("Irrigation (L/ha)", f"{liters:,.0f}")
        st.caption(f"ET₀={et0_val:.2f}  |  ETc={etc:.2f}  |  Effective Rain={peff:.2f}")
