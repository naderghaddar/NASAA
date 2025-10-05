import pandas as pd, requests

def fetch_nasa_power(lat: float, lon: float,
                     start="20000709", end="20250831") -> pd.DataFrame:
    """
    Daily point request to NASA POWER (AG community).
    Returns: Date, Temp, Humidity, Wind, Precip (all numeric)
    """
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?latitude={lat}&longitude={lon}&start={start}&end={end}"
        "&parameters=T2M,RH2M,WS10M,PRECTOTCORR&community=ag&format=JSON"
    )
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    data = r.json()["properties"]["parameter"]

    df = pd.DataFrame(data)
    df.index = pd.to_datetime(df.index)
    df = df.rename(columns={
        "T2M":"Temp", "RH2M":"Humidity", "WS10M":"Wind", "PRECTOTCORR":"Precip"
    }).reset_index().rename(columns={"index":"Date"})
    # Ensure proper types
    for c in ["Temp","Humidity","Wind","Precip"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna()
