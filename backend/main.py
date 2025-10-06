# backend/main.py
from __future__ import annotations

import os
from datetime import date as _date
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.io import fetch_nasa_power
from services.model import train_rf_models, recursive_forecast
from services.irrigation import irrigation_need
from services.advisory import farmer_recommendations


# ---------- App & CORS ----------
app = FastAPI(title="Farm Backend", version="1.0")

# Allow multiple origins via env (comma-separated). Example on Render:
# CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
_cors = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
origins = [o.strip() for o in _cors.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Models ----------
class ForecastReq(BaseModel):
    lat: float = 45.65
    lon: float = -73.38
    target_date: _date
    kc: float = Field(1.15, ge=0.3, le=1.5)
    soil_buffer_mm: float = 2.0
    eff_rain_factor: float = 0.8
    # Optional overrides; if omitted/invalid we compute a safe window below
    start: str | None = None  # "YYYYMMDD"
    end: str | None = None    # "YYYYMMDD"


class ForecastResp(BaseModel):
    target: str
    prediction: dict
    irrigation_mm: float
    et0: float
    etc: float
    peff: float
    recommendations: dict


# ---------- Helpers ----------
def _ymd(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y%m%d")


def _compute_fetch_window(body: ForecastReq) -> tuple[str, str]:
    """Return (start_YYYYMMDD, end_YYYYMMDD) with sane defaults."""
    t = pd.Timestamp(body.target_date)
    today = pd.Timestamp.today().normalize()

    # End = min(target, today, user_end if valid)
    end_user = pd.to_datetime(body.end, format="%Y%m%d", errors="coerce") if body.end else None
    end_ts = min([x for x in [t, today, end_user] if x is not None])

    # Start: prefer user start if valid, else same MMDD 5y earlier than end
    start_user = pd.to_datetime(body.start, format="%Y%m%d", errors="coerce") if body.start else None
    if start_user is not None:
        start_ts = start_user
    else:
        start_ts = pd.Timestamp(year=end_ts.year - 5, month=end_ts.month, day=end_ts.day)

    if start_ts > end_ts:
        raise HTTPException(status_code=400, detail="start date must be <= end date")

    return _ymd(start_ts), _ymd(end_ts)


# ---------- Routes ----------
@app.get("/health")
def health():
    return {"ok": True, "origins": origins}


@app.post("/api/forecast-advice", response_model=ForecastResp)
def forecast_advice(body: ForecastReq):
    # 0) Decide fetch window (robust defaults)
    start_str, end_str = _compute_fetch_window(body)

    # 1) Fetch + train
    df = fetch_nasa_power(body.lat, body.lon, start=start_str, end=end_str)
    if df.empty:
        raise HTTPException(status_code=502, detail="No usable NASA POWER data for that window.")

    df_feat, models = train_rf_models(df)

    # 2) Cap forecast horizon (avoid huge recursive loops)
    target_ts = pd.Timestamp(body.target_date)
    last_hist = df["Date"].max()
    horizon_days = (target_ts - last_hist).days
    MAX_HORIZON = int(os.getenv("MAX_HORIZON_DAYS", "120"))
    if horizon_days > MAX_HORIZON:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Target is {horizon_days} days past available data; "
                f"max forward is {MAX_HORIZON} days. Choose an earlier target date."
            ),
        )

    # 3) Forecast recursively to target
    future = recursive_forecast(df, models, target_ts)

    # 4) Extract target row
    sel = future[future["Date"] == target_ts]
    if sel.empty:
        raise HTTPException(status_code=500, detail="Internal error: target date row not produced.")
    pred_row = sel.iloc[0]

    temp = float(pred_row["Temp"])
    hum = float(pred_row["Humidity"])
    wind = float(pred_row["Wind"])
    precip = float(pred_row["Precip"])

    # 5) Irrigation + recommendations
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
        "recommendations": recs,
    }
