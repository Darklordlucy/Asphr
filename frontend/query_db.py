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
            cur.execute("""
                SELECT 
                    rs.id,
                    tc.congestion_level,
                    tc.speed_kmh,
                    ST_AsGeoJSON(ST_Centroid(rs.geometry))
                FROM road_segments rs
                JOIN LATERAL (
                    SELECT congestion_level, speed_kmh
                    FROM traffic_conditions
                    WHERE segment_id = rs.id
                    ORDER BY recorded_at DESC
                    LIMIT 1
                ) tc ON TRUE
                WHERE tc.congestion_level >= 2;
            """)
            
            rows = cur.fetchall()
            features = []
            for rid, level, speed, geom_json in rows:
                # Color code by congestion level:
                # 2 -> Red (Heavy), 3 -> Severe (Dark Red)
                if level == 3:
                    color = "#EF4444" # heavy red
                else:
                    color = "#F97316" # heavy orange/red
                
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(geom_json),
                    "properties": {
                        "segment_id": rid,
                        "congestion_level": level,
                        "speed_kmh": speed,
                        "color": color
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
