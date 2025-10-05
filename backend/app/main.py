from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import datetime as dt
import pandas as pd

from .core import (
    train_or_load_models, forecast, irrigation, advisory
)

app = FastAPI(title="Irrigation ML API", version="1.0.0")

# Allow local dev frontends; tighten in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # change to your domain(s) in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START = "20000709"
END   = "20250831"

class PredictRequest(BaseModel):
    lat: float = Field(..., description="Latitude in degrees (south is negative)")
    lon: float = Field(..., description="Longitude in degrees (west is negative)")
    target_date: str = Field(..., description="YYYY-MM-DD")
    kc: float = 1.15
    soil_buffer: float = 2.0

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/predict")
def predict(req: PredictRequest):
    target_date = dt.datetime.strptime(req.target_date, "%Y-%m-%d").date()

    payload = train_or_load_models(req.lat, req.lon, START, END)
    df_future = forecast(payload, target_date)
    row = df_future[df_future["Date"] == pd.Timestamp(target_date)].iloc[0].to_dict()

    irr, et0_val, etc, peff = irrigation(
        row["Temp"], row["Humidity"], row["Wind"], row["Precip"],
        req.lat, target_date, req.kc, soil_buffer=req.soil_buffer
    )
    recs = advisory(row, irr, etc, et0_val)

    return {
        "inputs": {
            "lat": req.lat, "lon": req.lon, "target_date": req.target_date,
            "kc": req.kc, "soil_buffer": req.soil_buffer
        },
        "prediction": {
            "temp": round(row["Temp"], 2),
            "humidity": round(row["Humidity"], 2),
            "wind": round(row["Wind"], 2),
            "precip": round(row["Precip"], 2),
        },
        "irrigation": {
            "irr_mm": round(irr, 2),
            "et0": round(et0_val, 2),
            "etc": round(etc, 2),
            "peff": round(peff, 2),
            "liters_per_hectare": round(irr * 10000, 0)
        },
        "advisory": recs,
    }
