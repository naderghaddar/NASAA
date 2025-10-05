import os
import math
import datetime as dt
import numpy as np
import pandas as pd
import requests
import joblib
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------
st.set_page_config(page_title="Global Smart Irrigation Planner", layout="wide")
st.title("🌾 Global Smart Irrigation & Farm Advisory Dashboard")

st.markdown("""
This tool predicts **weather**, **irrigation needs**, and provides smart recommendations  
for field work, pest alerts, frost risk, and spraying conditions — based on NASA POWER data.
""")

# -------------------------------------------------------------------
# USER INPUT
# -------------------------------------------------------------------
st.sidebar.header("Location & Parameters")
lat = st.sidebar.number_input("Latitude (°)", -60.0, 60.0, 45.65, step=0.01)
lon = st.sidebar.number_input("Longitude (°)", -180.0, 180.0, -73.38, step=0.01)
target_date = st.sidebar.date_input("Target date", value=dt.date.today() + dt.timedelta(days=3))
kc = st.sidebar.slider("Crop coefficient (Kc)", 0.6, 1.3, 1.15, 0.05)
soil_buffer = st.sidebar.slider("Soil moisture buffer (mm)", 0, 10, 2)
eff_rain_factor = 0.8
start, end = "20000709", "20250831"  # 22 years of history

# -------------------------------------------------------------------
# FETCH NASA POWER DATA
# -------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def fetch_nasa_power(lat, lon, start, end):
    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point?"
        f"latitude={lat}&longitude={lon}&start={start}&end={end}"
        f"&parameters=T2M,RH2M,WS10M,PRECTOTCORR&community=ag&format=JSON"
    )
    r = requests.get(url, timeout=60)
    if not r.ok:
        raise ValueError("Failed to fetch NASA POWER data.")
    data = r.json()
    df = pd.DataFrame(data["properties"]["parameter"])
    df.index = pd.to_datetime(df.index)
    df.rename(columns={
        "T2M": "Temp",
        "RH2M": "Humidity",
        "WS10M": "Wind",
        "PRECTOTCORR": "Precip"
    }, inplace=True)
    df = df.reset_index().rename(columns={"index": "Date"})
    return df

# -------------------------------------------------------------------
# FEATURE ENGINEERING
# -------------------------------------------------------------------
def add_features(df):
    out = df.copy()
    out["doy"] = out["Date"].dt.dayofyear
    out["sin_doy"] = np.sin(2 * np.pi * out["doy"] / 366)
    out["cos_doy"] = np.cos(2 * np.pi * out["doy"] / 366)
    for c in ["Temp", "Humidity", "Wind", "Precip"]:
        for lag in [1, 7, 14]:
            out[f"{c}_lag{lag}"] = out[c].shift(lag)
        out[f"{c}_roll7"] = out[c].rolling(7).mean()
    return out.dropna().reset_index(drop=True)

# -------------------------------------------------------------------
# MODEL TRAINING
# -------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def train_local_models(lat, lon, start, end):
    df = fetch_nasa_power(lat, lon, start, end)
    df = add_features(df)
    feats = [c for c in df.columns if c not in ["Date", "Temp", "Humidity", "Wind", "Precip"]]
    targets = ["Temp", "Humidity", "Wind", "Precip"]
    models = {}
    for t in targets:
        rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(df[feats], df[t])
        models[t] = rf
    return df, models

# -------------------------------------------------------------------
# FORECAST FUNCTION
# -------------------------------------------------------------------
def forecast(df, models, target_date):
    hist = df.copy().sort_values("Date").reset_index(drop=True)
    feats = [c for c in add_features(df).columns if c not in ["Date", "Temp", "Humidity", "Wind", "Precip"]]
    last_date = hist["Date"].iloc[-1]
    horizon_days = (pd.Timestamp(target_date) - last_date).days
    if horizon_days <= 0:
        st.warning("⚠️ Target date must be after last data point.")
        return hist
    max_horizon = 365 * 6
    horizon_days = min(horizon_days, max_horizon)

    for _ in range(horizon_days):
        next_date = hist["Date"].iloc[-1] + pd.Timedelta(days=1)
        tmp = pd.concat([hist, pd.DataFrame({"Date": [next_date]})], ignore_index=True)
        tmp = add_features(tmp)
        feat = tmp.iloc[[-1]][feats]
        preds = {t: models[t].predict(feat)[0] for t in models}
        new_row = pd.DataFrame([{
            "Date": next_date,
            "Temp": preds["Temp"],
            "Humidity": preds["Humidity"],
            "Wind": preds["Wind"],
            "Precip": max(preds["Precip"], 0)
        }])
        hist = pd.concat([hist, new_row], ignore_index=True)

    return hist

# -------------------------------------------------------------------
# IRRIGATION CALCULATIONS
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# HELPER: FARMER ADVISORY LOGIC
# -------------------------------------------------------------------
def farmer_recommendations(pred_row, irr, etc, et0_val):
    temp, hum, wind, precip = pred_row["Temp"], pred_row["Humidity"], pred_row["Wind"], pred_row["Precip"]
    recs = {}

    # Irrigation advice
    if precip > 5:
        recs["irrigation"] = f"💧 **Skip irrigation** — sufficient rainfall expected ({precip:.1f} mm)."
    elif irr > 5:
        recs["irrigation"] = f"🚜 **Irrigate**: {irr:.1f} mm recommended to meet crop needs (ETc={etc:.2f})."
    else:
        recs["irrigation"] = "✅ No irrigation needed — soil moisture adequate."

    # Pest alert (humidity + temp combo)
    if hum > 85 and 18 < temp < 28:
        recs["pest"] = "🐛 **High fungal disease risk** (e.g., blight, mildew). Consider fungicide."
    elif hum < 40:
        recs["pest"] = "🪳 **Low pest pressure** — dry conditions reduce infestation risk."
    else:
        recs["pest"] = "⚠️ Moderate pest risk — monitor fields regularly."

    # Field work
    if precip > 3 or hum > 90:
        recs["field"] = "❌ Too wet for tractor operations. Wait for drier conditions."
    elif wind > 7:
        recs["field"] = "🌬️ Windy — spraying or seeding not recommended."
    else:
        recs["field"] = "✅ Good window for field work or seeding."

    # Frost risk
    if temp < 2:
        recs["frost"] = "❄️ **Frost risk detected** — protect seedlings or delay planting."
    elif temp < 6:
        recs["frost"] = "⚠️ Mild cold risk — avoid spraying overnight."
    else:
        recs["frost"] = "🌡️ No frost risk for this period."

    # Spray window
    if 50 < hum < 70 and wind < 5 and precip < 0.5:
        recs["spray"] = "💉 **Excellent conditions for spraying** — low wind, dry air, no rain forecast."
    else:
        recs["spray"] = "🚫 Suboptimal spraying conditions."

    return recs

# -------------------------------------------------------------------
# MAIN ACTION
# -------------------------------------------------------------------
if st.button("🌤️ Generate Farm Forecast"):
    with st.spinner("⏳ Fetching NASA POWER data and training model..."):
        df, models = train_local_models(lat, lon, start, end)
    with st.spinner("🔮 Generating forecast and recommendations..."):
        future = forecast(df, models, target_date)
        pred_row = future[future["Date"] == pd.Timestamp(target_date)].iloc[0]
        irr, et0_val, etc, peff = irrigation(
            pred_row["Temp"], pred_row["Humidity"], pred_row["Wind"],
            pred_row["Precip"], lat, target_date, kc
        )
        recs = farmer_recommendations(pred_row, irr, etc, et0_val)
        liters = irr * 10000

    # ------------------ DISPLAY -------------------
    st.success(f"✅ Forecast for {target_date.isoformat()} at lat={lat}, lon={lon}")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("🌡️ Temperature (°C)", f"{pred_row['Temp']:.1f}")
        st.metric("💧 Humidity (%)", f"{pred_row['Humidity']:.0f}")
        st.metric("🌬️ Wind Speed (m/s)", f"{pred_row['Wind']:.2f}")
        st.metric("🌦️ Precipitation (mm)", f"{pred_row['Precip']:.2f}")
    with col2:
        st.metric("💦 Irrigation Need (mm)", f"{irr:.2f}")
        st.metric("💧 Water Volume (L/ha)", f"{liters:,.0f}")
        st.caption(f"ET₀={et0_val:.2f} | ETc={etc:.2f} | EffRain={peff:.2f}")

    st.divider()
    st.subheader("🌍 Farm Advisory Summary")

    st.markdown(f"""
    - {recs['irrigation']}
    - {recs['pest']}
    - {recs['field']}
    - {recs['spray']}
    - {recs['frost']}
    """)

    st.divider()
    st.caption("Data source: NASA POWER • Advisory is indicative only and depends on local conditions.")
