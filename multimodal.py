import requests, math
from typing import Dict, Any, List, Tuple

class ORSClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.openrouteservice.org/v2/directions/driving-car"

    @staticmethod
    def _haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        R = 6371.0088
        lat1, lon1 = map(math.radians, a)
        lat2, lon2 = map(math.radians, b)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2*R*math.asin(math.sqrt(h))

    def _build_body(self, origin, dest, alt_count, avoid_tolls, use_alternatives=True):
        body = {
            "coordinates": [[origin[1], origin[0]], [dest[1], dest[0]]],
            "instructions": True,
            "extra_info": ["waytype", "tollways"],
            "preference": "recommended" if use_alternatives else "fastest",
        }
        if use_alternatives:
            body["alternative_routes"] = {
                "share_factor": 0.6,
                "target_count": max(1, alt_count),
                "weight_factor": 1.4
            }
        if avoid_tolls:
            body["options"] = {"avoid_features": ["tollways"]}
        return body

    def fetch_routes(self, origin: Tuple[float, float], dest: Tuple[float, float], alt_count: int = 3, avoid_tolls: bool = False) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Missing ORS_API_KEY in Streamlit secrets."}
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}

        crow_km = self._haversine_km(origin, dest)
        use_alternatives = crow_km <= 100.0  # alternatives only if ≤ 100 km
        body = self._build_body(origin, dest, alt_count, avoid_tolls, use_alternatives=use_alternatives)
        try:
            resp = requests.post(self.url, json=body, headers=headers, timeout=60)
        except requests.RequestException as e:
            return {"error": f"Network error contacting ORS: {e}"}

        if resp.ok:
            try:
                return resp.json()
            except Exception:
                return {"error": "Failed to parse ORS JSON response."}

        # Retry without alternatives if 400 mentions alt-routes limit
        if resp.status_code == 400 and use_alternatives:
            try:
                msg = resp.json().get('error', {}).get('message')
            except Exception:
                msg = resp.text
            if msg and ('100000.0' in msg or 'alternative Routes algorithm' in msg):
                body2 = self._build_body(origin, dest, 1, avoid_tolls, use_alternatives=False)
                try:
                    resp2 = requests.post(self.url, json=body2, headers=headers, timeout=60)
                    if resp2.ok:
                        return resp2.json()
                    else:
                        try:
                            msg2 = resp2.json().get('error', {}).get('message') or resp2.text
                        except Exception:
                            msg2 = resp2.text
                        return {"error": f"ORS HTTP {resp2.status_code} on retry: {msg2}"}
                except requests.RequestException as e:
                    return {"error": f"Network error on retry: {e}"}

        try:
            msg = resp.json().get('error', {}).get('message') or resp.text
        except Exception:
            msg = resp.text
        return {"error": f"ORS HTTP {resp.status_code}: {msg}"}

    @staticmethod
    def parse_routes(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(resp, dict) or resp.get('error'):
            return []
        routes = []

        def summarize_roads(steps):
            names = []
            for s in steps:
                nm = s.get("name") or s.get("instruction")
                if nm and nm != "-":
                    names.append(nm)
            seen, out = set(), []
            for nm in names:
                if nm not in seen:
                    out.append(nm)
                    seen.add(nm)
                if len(out) >= 6:
                    break
            return ", ".join(out)

        # ORS GeoJSON FeatureCollection
        if 'features' in resp:
            for feat in resp.get("features", []):
                props = feat.get("properties", {})
                segs = props.get("segments", [])
                steps_all = []
                for seg in segs:
                    for s in seg.get("steps", []):
                        steps_all.append({
                            "instruction": s.get("instruction"),
                            "name": s.get("name") or s.get("instruction"),
                            "distance_m": s.get("distance", 0),
                            "duration_s": s.get("duration", 0),
                        })
                routes.append({
                    "distance_km": props.get("summary", {}).get("distance", 0)/1000.0,
                    "duration_min": props.get("summary", {}).get("duration", 0)/60.0,
                    "geometry": feat.get("geometry", {}),
                    "steps": steps_all,
                    "roads_summary": summarize_roads(steps_all),
                    "provider": "ORS"
                })

        # Non-GeoJSON variant
        elif 'routes' in resp:
            for r in resp.get('routes', []):
                summary = r.get('summary', {})
                steps_all = []
                for s in r.get('segments', []):
                    for st in s.get('steps', []):
                        steps_all.append({
                            "instruction": st.get("instruction"),
                            "name": st.get("name") or st.get("instruction"),
                            "distance_m": st.get("distance", 0),
                            "duration_s": st.get("duration", 0),
                        })
                geom = r.get('geometry')
                if isinstance(geom, dict) and geom.get('type') == 'LineString':
                    geometry = geom
                else:
                    geometry = {"type": "LineString", "coordinates": r.get('coordinates', [])}
                routes.append({
                    "distance_km": summary.get("distance", 0)/1000.0,
                    "duration_min": summary.get("duration", 0)/60.0,
                    "geometry": geometry,
                    "steps": steps_all,
                    "roads_summary": summarize_roads(steps_all),
                    "provider": "ORS"
                })

        return routes
