import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from optimization import compute_cost_and_emissions, score_routes
from map_utils import draw_routes_map
from multimodal import ORSClient

st.set_page_config(page_title="Multi‑Modal Route Optimizer", layout="wide")

# Inject CSS
from pathlib import Path
css_path = Path("assets/ui.css")
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    .header-gradient {background: linear-gradient(90deg, #7c3aed 0%, #22d3ee 50%, #60a5fa 100%); padding:14px 18px; border-radius:10px; color:#0b1220; font-weight:700}
    .badge { display:inline-block; padding:2px 8px; border-radius: 14px; font-size:11px; }
    .badge.recommended { background:#10b98120; color:#10b981; border:1px solid #10b98155; }
    .badge.alt { background:#3b82f620; color:#3b82f6; border:1px solid #3b82f655; }
    .card { background:#0b1220; border:1px solid #293246; border-radius: 10px; padding: 12px; }
    .card .value { font-size: 22px; font-weight: 700; }
    .hr-soft { border:none; height:1px; background:#293246; margin: 14px 0; }
    .table-note { font-size:12px; color:#94a3b8; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="header-gradient">🧭 Multi‑Modal Route Optimizer</div>', unsafe_allow_html=True)
st.caption("Find & evaluate road routes by Distance, Time, Cost, CO₂ — with a recommended path highlighted")

# Sidebar
st.sidebar.header("Global Configuration")
use_static = st.sidebar.checkbox("Use static points", value=True)
static_from = {
    "Kolkata (Esplanade)": (22.5667, 88.3667),
    "Howrah Maidan": (22.5892, 88.3475),
}
static_to = {
    "Salt Lake (Sector V)": (22.5792, 88.4317),
    "Kharagpur": (22.3400, 87.3250),
}

if use_static:
    origin_label = st.sidebar.selectbox("From", list(static_from.keys()), index=0)
    dest_label = st.sidebar.selectbox("To", list(static_to.keys()), index=0)
    origin = static_from[origin_label]
    dest = static_to[dest_label]
else:
    origin = (
        st.sidebar.number_input("From Lat", value=22.5667, format="%.6f"),
        st.sidebar.number_input("From Lon", value=88.3667, format="%.6f")
    )
    dest = (
        st.sidebar.number_input("To Lat", value=22.5792, format="%.6f"),
        st.sidebar.number_input("To Lon", value=88.4317, format="%.6f")
    )

st.sidebar.subheader("KPIs & Pricing")
co2_g_per_km = st.sidebar.number_input("CO₂ intensity (g/km)", value=120.0)
fuel_economy = st.sidebar.number_input("Fuel economy (km/l)", value=15.0)
fuel_price = st.sidebar.number_input("Fuel price (₹/l)", value=110.0)

st.sidebar.subheader("Alternatives & Avoidance")
alt_count = st.sidebar.slider("Alternatives (≤100 km)", 1, 5, 3)
avoid_tolls = st.sidebar.checkbox("Avoid tollways", value=False)

st.sidebar.subheader("Weights (Scoring)")
weights = {
    "distance_km": st.sidebar.slider("Distance", 0.0, 3.0, 1.0),
    "duration_min": st.sidebar.slider("Time", 0.0, 3.0, 1.0),
    "cost_inr": st.sidebar.slider("Cost", 0.0, 3.0, 1.0),
    "emissions_kg": st.sidebar.slider("CO₂", 0.0, 3.0, 1.0),
}

ORS_API_KEY = st.secrets.get("ORS_API_KEY", "")
if not ORS_API_KEY:
    st.sidebar.error("Set ORS_API_KEY in Streamlit Cloud → App settings → Secrets")

run = st.sidebar.button("🔎 Compute & Optimize")

# Session state
for key in ["routes", "df", "scored_df", "best_idx", "origin", "dest", "message"]:
    if key not in st.session_state:
        st.session_state[key] = None

@st.cache_data(show_spinner=False)
def _cached_fetch(origin, dest, alt_count, avoid_tolls, api_key):
    client = ORSClient(api_key)
    return client.fetch_routes(origin, dest, alt_count=alt_count, avoid_tolls=avoid_tolls)

if run:
    try:
        if origin == dest:
            st.session_state.message = "Origin and destination are identical. Choose different points."
        else:
            resp = _cached_fetch(origin, dest, alt_count, avoid_tolls, ORS_API_KEY)
            if isinstance(resp, dict) and resp.get('error'):
                st.session_state.message = resp['error']
                st.session_state.routes = None
            else:
                routes = ORSClient.parse_routes(resp)
                if not routes:
                    st.session_state.message = "No routes parsed. Try shorter trips (≤100 km) for alternatives, or check quota."
                    st.session_state.routes = None
                else:
                    rows = []
                    for i, r in enumerate(routes):
                        dist = r.get("distance_km", 0.0)
                        duration = r.get("duration_min", 0.0)
                        cost_inr, emissions_kg = compute_cost_and_emissions(dist, fuel_economy, fuel_price, co2_g_per_km)
                        rows.append({
                            "Route": i,
                            "distance_km": round(dist, 2),
                            "duration_min": round(duration, 2),
                            "cost_inr": cost_inr,
                            "emissions_kg": emissions_kg,
                            "roads_summary": r.get("roads_summary", ""),
                        })
                    df = pd.DataFrame(rows)
                    scored_df, best_idx = score_routes(df, weights)

                    st.session_state.routes = routes
                    st.session_state.df = df
                    st.session_state.scored_df = scored_df
                    st.session_state.best_idx = best_idx
                    st.session_state.origin = origin
                    st.session_state.dest = dest
                    st.session_state.message = None
    except Exception as e:
        st.session_state.message = f"Unexpected error: {e}"

# Layout blocks
if st.session_state.message:
    st.error(st.session_state.message)

if st.session_state.routes and st.session_state.scored_df is not None:
    st.subheader("All Available Routes")
    df = st.session_state.scored_df.copy()
    df["Tag"] = np.where(df["tag"] == "recommended", "<span class='badge recommended'>Recommended</span>", "<span class='badge alt'>Alt</span>")
    disp = df[["Route", "distance_km", "duration_min", "cost_inr", "emissions_kg", "roads_summary", "score", "Tag"]]
    st.write("<div class='table-note'>Scores reflect your sidebar weights (MinMax). Lower is better.</div>", unsafe_allow_html=True)
    st.write(disp.to_html(escape=False, index=False), unsafe_allow_html=True)
    st.markdown("<hr class='hr-soft'>", unsafe_allow_html=True)

    st.subheader("Recommended Route")
    best_row = df.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(f"<div class='card'><div>Distance (km)</div><div class='value'>{best_row['distance_km']}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='card'><div>Time (min)</div><div class='value'>{best_row['duration_min']}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='card'><div>Cost (₹)</div><div class='value'>{best_row['cost_inr']}</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='card'><div>CO₂ (kg)</div><div class='value'>{best_row['emissions_kg']}</div></div>", unsafe_allow_html=True)
    with c5: st.markdown(f"<div class='card'><div>Score</div><div class='value'>{best_row['score']:.3f}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='hr-soft'>", unsafe_allow_html=True)

    st.subheader("Route Visualization")
    rec_route_id = int(best_row["Route"]) if st.session_state.best_idx != -1 else 0
    draw_routes_map(st.session_state.origin, st.session_state.dest, st.session_state.routes, rec_route_id)

    st.markdown("<hr class='hr-soft'>", unsafe_allow_html=True)

    st.subheader("Route Analytics")
    # Altair horizontal bars comparing metrics
    base = alt.Chart(df).encode(y=alt.Y('Route:N', sort=None))
    for field, title in [("distance_km","Distance (km)"),("duration_min","Time (min)"),("cost_inr","Cost (₹)"),("emissions_kg","CO₂ (kg)")]:
        chart = base.mark_bar().encode(x=alt.X(f'{field}:Q', title=title), color=alt.Color('Route:N', legend=None))
        st.altair_chart(chart.properties(height=200), use_container_width=True)

    st.subheader("Turn‑by‑turn (Road Names) — Recommended")
    steps_df = pd.DataFrame(st.session_state.routes[rec_route_id].get("steps", []))
    if not steps_df.empty:
        steps_df = steps_df[["name", "instruction", "distance_m", "duration_s"]]
        steps_df.rename(columns={"name": "Road / Street", "instruction": "Instruction", "distance_m": "Segment (m)", "duration_s": "Segment (s)"}, inplace=True)
    st.dataframe(steps_df, use_container_width=True)
