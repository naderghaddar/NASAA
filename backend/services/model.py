import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from .features import add_features, feature_columns, TARGETS

def train_rf_models(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Trains 4 RF regressors (Temp, Humidity, Wind, Precip) on engineered features.
    Returns the *feature-engineered* DataFrame used and the dict of models.
    """
    df_feat = add_features(df)
    feats = feature_columns(df_feat)
    models = {}
    for t in TARGETS:
        rf = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
        rf.fit(df_feat[feats], df_feat[t])
        models[t] = rf
    return df_feat, models

def recursive_forecast(df_hist: pd.DataFrame, models: dict,
                       target_date: pd.Timestamp) -> pd.DataFrame:
    """
    Rolls daily to target_date, each time generating features from the expanding
    history and predicting the next day for all 4 targets.
    Returns a DataFrame from the original start through target_date.
    """
    hist = df_hist.copy().sort_values("Date").reset_index(drop=True)
    from .features import add_features, feature_columns
    # compute initial feature set to know names
    feats = feature_columns(add_features(hist))

    last_date = hist["Date"].iloc[-1]
    horizon_days = (pd.Timestamp(target_date) - last_date).days
    if horizon_days <= 0:
        return hist

    horizon_days = min(horizon_days, 365*6)  # safety cap

    for _ in range(horizon_days):
        next_date = hist["Date"].iloc[-1] + pd.Timedelta(days=1)
        tmp = pd.concat([hist, pd.DataFrame({"Date":[next_date]})], ignore_index=True)
        tmp_feat = add_features(tmp)
        feat = tmp_feat.iloc[[-1]][feats]  # last row features
        preds = {t: models[t].predict(feat)[0] for t in models}
        new_row = {"Date":next_date, **preds}
        # Precip cannot be negative
        new_row["Precip"] = max(new_row["Precip"], 0.0)
        hist = pd.concat([hist, pd.DataFrame([new_row])], ignore_index=True)

    return hist
