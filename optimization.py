import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


def compute_cost_and_emissions(distance_km: float, fuel_economy_kmpl: float, fuel_price_inr: float, co2_g_per_km: float):
    litres = max(distance_km, 0.0) / max(fuel_economy_kmpl, 0.0001)
    cost_inr = litres * fuel_price_inr
    emissions_kg = (co2_g_per_km * max(distance_km, 0.0)) / 1000.0
    return round(cost_inr, 2), round(emissions_kg, 3)


def score_routes(routes_df: pd.DataFrame, weights: dict):
    df = routes_df.copy()
    if df.empty:
        df["score"] = []
        return df, -1
    cols = ["distance_km", "duration_min", "cost_inr", "emissions_kg"]
    scaler = MinMaxScaler()
    norm = scaler.fit_transform(df[cols])
    w = np.array([weights.get(c, 1.0) for c in cols])
    scores = (norm @ w.reshape(-1, 1)).flatten()
    df["score"] = scores
    best_idx = int(np.argmin(scores))
    df["tag"] = ""
    df.loc[df.index[best_idx], "tag"] = "recommended"
    return df.sort_values(by="score").reset_index(drop=True), best_idx
