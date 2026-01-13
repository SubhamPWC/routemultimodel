# Multi‑Modal Route Optimizer — Streamlit (Dark UI + Google‑style Map Highlight + KPIs)

This Streamlit app provides a sleek dashboard (similar to your screenshot) with:

- **Dark UI** header and sections
- **All Available Routes** table with **road names**, KPIs (Distance, Time, Cost, CO₂), **Score**, and **Tag**
- **Recommended Route** summary cards (Distance, Time, Cost, CO₂, Score)
- **Route Visualization** map (CartoDB Dark Matter) with **Google‑style highlighted paths**
- **Route Analytics** charts (Distance, Time, Cost, Emissions comparisons)

The app uses **OpenRouteService (ORS)** (OpenStreetMap data) to fetch up to several **alternative routes**
*(when allowed by the public API for shorter trips)*, and robustly falls back to the single **fastest** route
for longer trips. Turn‑by‑turn **road/street names** are displayed for the recommended route.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud
1) Push this folder to a public GitHub repo.
2) New app → **Main file**: `app.py`
3) **App settings → Secrets**:
```toml
ORS_API_KEY = "YOUR_ORS_API_KEY"
```
