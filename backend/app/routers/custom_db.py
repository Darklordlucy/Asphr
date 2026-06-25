import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.config import get_db, settings

router = APIRouter(prefix="/api/v1/custom-db", tags=["CustomDB"])

@router.get("/popular_places")
async def get_popular_places(db: AsyncSession = Depends(get_db)):
    """Retrieve Mumbai popular places with geometries from database."""
    try:
        query = text("""
            SELECT name, category, popularity_score, ST_AsGeoJSON(geometry) 
            FROM popular_places;
        """)
        result = await db.execute(query)
        rows = result.fetchall()
        features = []
        for name, category, score, geom_json in rows:
            features.append({
                "type": "Feature",
                "geometry": json.loads(geom_json),
                "properties": {
                    "name": name,
                    "category": category,
                    "popularity_score": float(score or 0.0)
                }
            })
        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch popular places: {str(e)}"
        )

@router.get("/weather_grid")
async def get_weather_grid(db: AsyncSession = Depends(get_db)):
    """Retrieve weather grid cells with conditions and temperature from database."""
    try:
        query = text("""
            SELECT id, temperature, humidity, visibility_km, precipitation_mm, wind_speed_kmh, weather_condition, ST_AsGeoJSON(cell_geometry) 
            FROM weather_grid;
        """)
        result = await db.execute(query)
        rows = result.fetchall()
        features = []
        for cid, temp, hum, vis, precip, wind, cond, geom_json in rows:
            features.append({
                "type": "Feature",
                "geometry": json.loads(geom_json),
                "properties": {
                    "id": cid,
                    "temperature": float(temp or 0.0),
                    "humidity": float(hum or 0.0),
                    "visibility_km": float(vis or 0.0),
                    "precipitation_mm": float(precip or 0.0),
                    "wind_speed_kmh": float(wind or 0.0),
                    "weather_condition": cond or "clear"
                }
            })
        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch weather grid: {str(e)}"
        )

@router.get("/heavy_traffic")
async def get_heavy_traffic():
    """Fetch live heavy traffic incident points from TomTom API for MMR bbox."""
    try:
        key = settings.TOMTOM_API_KEY
        if not key:
            key = "Hbd95vTMExHxaAjqy8HGs6J0EEXLDZo9"
            
        url = 'https://api.tomtom.com/traffic/services/5/incidentDetails'
        params = {
            'key': key,
            'bbox': '72.75,18.90,73.20,19.50',
            'fields': '{incidents{type,geometry{type,coordinates},properties{iconCategory,magnitudeOfDelay,delay,events{description}}}}'
        }
        
        async with httpx.AsyncClient() as client:
            res = await client.get(url, params=params, timeout=10.0)
            
        if res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"TomTom API failed with status {res.status_code}"
            )
            
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
            
            # Filter for heavy traffic/jams (congestion icon 6 or major magnitude >= 2)
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
                point_coords = coords[len(coords) // 2]
            elif geom_type == 'Polygon' and len(coords) > 0 and len(coords[0]) > 0:
                point_coords = coords[0][0]
            else:
                point_coords = coords[0] if isinstance(coords[0], list) and not isinstance(coords[0][0], list) else [72.8777, 19.0760]

            # Map magnitude to speed/congestion levels
            congestion_level = 3 if mag >= 3 else 2
            color = "#EF4444" if congestion_level == 3 else "#F97316"
            
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
            
        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch heavy traffic: {str(e)}"
        )
