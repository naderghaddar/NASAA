from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import date as _date
import pandas as pd

from services.io import fetch_nasa_power
from services.model import train_rf_models, recursive_forecast
from services.irrigation import irrigation_need
from services.advisory import farmer_recommendations

app = FastAPI(title="Farm Backend", version="1.0")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class ForecastReq(BaseModel):
    lat: float = 45.65
    lon: float = -73.38
    target_date: _date
    kc: float = Field(1.15, ge=0.3, le=1.5)
    soil_buffer_mm: float = 2.0
    eff_rain_factor: float = 0.8
    start: str = "20000709"
    end: str   = "20250831"

class ForecastResp(BaseModel):
    target: str
    prediction: dict
    irrigation_mm: float
    et0: float
    etc: float
    peff: float
    recommendations: dict

@app.get("/health")
def health(): return {"ok": True}

@app.post("/api/forecast-advice", response_model=ForecastResp)
def forecast_advice(body: ForecastReq):
    # 1) fetch + train
    df = fetch_nasa_power(body.lat, body.lon, body.start, body.end)
    df_feat, models = train_rf_models(df)

    # 2) forecast recursively to target
    future = recursive_forecast(df, models, pd.Timestamp(body.target_date))

    # 3) pick target row
    pred_row = future[future["Date"] == pd.Timestamp(body.target_date)].iloc[0]
    temp = float(pred_row["Temp"]); hum = float(pred_row["Humidity"])
    wind = float(pred_row["Wind"]); precip = float(pred_row["Precip"])

    # 4) irrigation + recs
    irr, et0, etc, peff = irrigation_need(
        temp, hum, wind, precip, body.lat, body.target_date, body.kc,
        body.eff_rain_factor, body.soil_buffer_mm
    )
    recs = farmer_recommendations(temp, hum, wind, precip, irr, etc, et0)

    return {
        "target": body.target_date.isoformat(),
        "prediction": {"Temp": temp, "Humidity": hum, "Wind": wind, "Precip": precip},
        "irrigation_mm": float(irr),
        "et0": float(et0),
        "etc": float(etc),
        "peff": float(peff),
        "recommendations": recs
    }
