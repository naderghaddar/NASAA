import numpy as np, pandas as pd

TARGETS = ["Temp","Humidity","Wind","Precip"]

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Your original feature engineering (lags, rolling, DOY sin/cos).
    Input df requires columns: Date, Temp, Humidity, Wind, Precip
    """
    out = df.copy()
    out["doy"] = out["Date"].dt.dayofyear
    out["sin_doy"] = np.sin(2*np.pi*out["doy"]/366)
    out["cos_doy"] = np.cos(2*np.pi*out["doy"]/366)
    for c in TARGETS:
        for lag in [1,7,14]:
            out[f"{c}_lag{lag}"] = out[c].shift(lag)
        out[f"{c}_roll7"] = out[c].rolling(7).mean()
    return out.dropna().reset_index(drop=True)

def feature_columns(df_feat: pd.DataFrame) -> list[str]:
    return [c for c in df_feat.columns if c not in ["Date"] + TARGETS]
