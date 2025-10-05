import requests
import pandas as pd
import matplotlib.pyplot as plt

# Choose a location and dates
lat, lon = 45.65, -73.38     # Toronto
start, end = "20000709", "20250818"

# ---------- 1) NASA POWER (historical/recent) ----------
power_url = (
    f"https://power.larc.nasa.gov/api/temporal/daily/point?"
    f"latitude={lat}&longitude={lon}&start={start}&end={end}"
    f"&parameters=T2M,RH2M,WS10M,PRECTOTCORR&community=ag&format=JSON"
)
power_data = requests.get(power_url).json()

# Extract data
df_power = pd.DataFrame(power_data["properties"]["parameter"])
df_power.index = pd.to_datetime(df_power.index)
df_power.rename(columns={
    "T2M": "Temp (°C)",
    "RH2M": "Humidity (%)",
    "WS10M": "Wind (m/s)",
    "PRECTOTCORR": "Precip (mm)"
}, inplace=True)

print("\nNASA POWER sample:\n", df_power.head())

# ---------- 2) Open-Meteo (forecast) ----------
meteourl = (
    f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,precipitation_probability"
    "&forecast_days=7&timezone=auto"
)
r = requests.get(meteourl).json()
df_meteo = pd.DataFrame(r["hourly"])
df_meteo["time"] = pd.to_datetime(df_meteo["time"])
df_meteo.set_index("time", inplace=True)
df_meteo.rename(columns={
    "temperature_2m": "Temp (°C)",
    "relative_humidity_2m": "Humidity (%)",
    "wind_speed_10m": "Wind (m/s)",
    "precipitation": "Precip (mm)",
    "precipitation_probability": "PrecipProb (%)"
}, inplace=True)

print("\nOpen-Meteo sample:\n", df_meteo.head())

# ---------- 3) Plot ----------
plt.figure(figsize=(12, 7))
plt.title("Weather Overview – Toronto (NASA POWER + Open-Meteo)")

# Plot daily averages from POWER
df_power["Temp (°C)"].plot(label="Temp (NASA)", color="orange", marker="o")
plt.ylabel("Temp (°C)")

# Create twin axis for precipitation
ax2 = plt.twinx()
ax2.bar(df_power.index, df_power["Precip (mm)"], color="skyblue", alpha=0.4, label="Precip (NASA)")
ax2.set_ylabel("Precipitation (mm)")

plt.legend(loc="upper left")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

# Optional: save CSVs
df_power.to_csv("nasa_power_data.csv")
df_meteo.to_csv("open_meteo_data.csv")
