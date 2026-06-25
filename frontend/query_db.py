import os
import sys
import json
import psycopg2

def load_db_url():
    # Look for backend/.env relative to this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_env = os.path.join(os.path.dirname(current_dir), 'backend', '.env')
    if os.path.exists(backend_env):
        with open(backend_env, 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    url = line.split('=', 1)[1].strip()
                    if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
                        url = url[1:-1]
                    return url
    return os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres")

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing table argument"}))
        sys.exit(1)

    table = sys.argv[1]
    db_url = load_db_url()

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        if table == "popular_places":
            cur.execute("SELECT name, category, popularity_score, ST_AsGeoJSON(geometry) FROM popular_places;")
            rows = cur.fetchall()
            features = []
            for name, category, score, geom_json in rows:
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(geom_json),
                    "properties": {
                        "name": name,
                        "category": category,
                        "popularity_score": score
                    }
                })
            print(json.dumps({"type": "FeatureCollection", "features": features}))

        elif table == "weather_grid":
            cur.execute("SELECT id, temperature, humidity, visibility_km, precipitation_mm, wind_speed_kmh, weather_condition, ST_AsGeoJSON(cell_geometry) FROM weather_grid;")
            rows = cur.fetchall()
            features = []
            for cid, temp, hum, vis, precip, wind, cond, geom_json in rows:
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(geom_json),
                    "properties": {
                        "id": cid,
                        "temperature": temp,
                        "humidity": hum,
                        "visibility_km": vis,
                        "precipitation_mm": precip,
                        "wind_speed_kmh": wind,
                        "weather_condition": cond
                    }
                })
            print(json.dumps({"type": "FeatureCollection", "features": features}))

        elif table == "heavy_traffic":
            # 1. Load TomTom API key
            key = None
            backend_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env')
            if os.path.exists(backend_env):
                with open(backend_env, 'r') as f:
                    for line in f:
                        if line.startswith('TOMTOM_API_KEY='):
                            key = line.split('=', 1)[1].strip()
                            if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
                                key = key[1:-1]
                            break
            if not key:
                key = os.environ.get("TOMTOM_API_KEY", "Hbd95vTMExHxaAjqy8HGs6J0EEXLDZo9")

            # 2. Call TomTom Incident Details API for MMR bbox
            # BBox covers CSMT to Virar, Thane to Panvel (minLon, minLat, maxLon, maxLat)
            url = 'https://api.tomtom.com/traffic/services/5/incidentDetails'
            params = {
                'key': key,
                'bbox': '72.75,18.90,73.20,19.50',
                'fields': '{incidents{type,geometry{type,coordinates},properties{iconCategory,magnitudeOfDelay,delay,events{description}}}}'
            }
            
            import httpx
            res = httpx.get(url, params=params, timeout=10.0)
            if res.status_code != 200:
                print(json.dumps({"error": f"TomTom API failed with status {res.status_code}"}))
                sys.exit(1)
                
            data = res.json()
            incidents = data.get('incidents', [])
            
            features = []
            for inc in incidents:
                props = inc.get('properties', {})
                cat = props.get('iconCategory')
                mag = props.get('magnitudeOfDelay', 0)
                delay = props.get('delay', 0) or 0
                events = props.get('events', [])
                desc = events[0].get('description', 'Heavy Traffic') if events else 'Heavy Traffic'
                
                # Filter for actual heavy traffic/jams (congestion icon 6 or major magnitude >= 2)
                if cat != 6 and mag < 2:
                    continue
                
                geom = inc.get('geometry', {})
                geom_type = geom.get('type')
                coords = geom.get('coordinates', [])
                
                if not coords:
                    continue
                    
                # Determine centroid point coordinates
                if geom_type == 'Point':
                    point_coords = coords
                elif geom_type == 'LineString':
                    # Use the midpoint of the LineString
                    point_coords = coords[len(coords) // 2]
                elif geom_type == 'Polygon' and len(coords) > 0 and len(coords[0]) > 0:
                    point_coords = coords[0][0]
                else:
                    point_coords = coords[0] if isinstance(coords[0], list) and not isinstance(coords[0][0], list) else [72.8777, 19.0760]

                # Map magnitude to speed/congestion levels for UI styling compatibility
                # TomTom magnitudes: 2 -> Moderate, 3 -> Major, 4 -> Standstill
                congestion_level = 3 if mag >= 3 else 2
                color = "#EF4444" if congestion_level == 3 else "#F97316"
                
                # Estimate speed or generate label details
                speed = round(72.0 / (delay / 60.0 + 1.0), 1) if delay > 0 else round(30.0 - mag * 4.0, 1)
                if speed < 5:
                    speed = 5.0
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": point_coords
                    },
                    "properties": {
                        "name": desc,
                        "congestion_level": congestion_level,
                        "speed_kmh": speed,
                        "color": color,
                        "delay_sec": delay,
                        "magnitude": mag
                    }
                })
                
            print(json.dumps({"type": "FeatureCollection", "features": features}))

        else:
            print(json.dumps({"error": "Unknown table requested"}))
            sys.exit(1)

        cur.close()
        conn.close()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
