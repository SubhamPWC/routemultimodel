import folium
from streamlit_folium import st_folium

RECOMMENDED_COLOR = "#3b82f6"  # blue
ALT_COLORS = ["#22d3ee", "#a78bfa", "#10b981", "#f59e0b", "#ef4444"]


def _style(color: str, weight: int = 7, opacity: float = 0.95):
    return {"color": color, "weight": weight, "opacity": opacity}


def draw_routes_map(origin, dest, routes, recommended_index: int):
    center_lat = (origin[0] + dest[0]) / 2.0
    center_lon = (origin[1] + dest[1]) / 2.0
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="CartoDB dark_matter")

    folium.CircleMarker([origin[0], origin[1]], radius=6, color="#22d3ee", fill=True, fill_opacity=0.95, popup="From").add_to(m)
    folium.CircleMarker([dest[0], dest[1]], radius=6, color="#f59e0b", fill=True, fill_opacity=0.95, popup="To").add_to(m)

    for idx, r in enumerate(routes):
        geom = r.get('geometry')
        if not isinstance(geom, dict):
            continue
        rec = (idx == recommended_index)
        color = RECOMMENDED_COLOR if rec else ALT_COLORS[idx % len(ALT_COLORS)]
        weight = 10 if rec else 6
        tooltip = f"{'Recommended' if rec else 'Alternative ' + str(idx)} • {r.get('distance_km',0):.1f} km, {r.get('duration_min',0):.1f} min"

        # GeoJSON layer (Leaflet consumes [lon, lat])
        gj = folium.GeoJson(data=geom, style_function=lambda x: _style(color, weight=weight, opacity=0.95), name=f"route_{idx}")
        gj.add_child(folium.Tooltip(tooltip))
        gj.add_to(m)

        # Extra glow for recommended: shadow + top stroke
        coords = []
        if geom.get('type') == 'LineString':
            coords = [(lat, lon) for lon, lat in geom.get('coordinates', [])]
        elif geom.get('type') == 'MultiLineString':
            for ln in geom.get('coordinates', []):
                coords.extend([(lat, lon) for lon, lat in ln])
        if rec and coords:
            folium.PolyLine(coords, color="#000000", weight=14, opacity=0.35).add_to(m)
            folium.PolyLine(coords, color=color, weight=8, opacity=0.98).add_to(m)

    folium.LayerControl().add_to(m)
    return st_folium(m, height=560)
