"""
Weather Service
===============
Fetches real-time weather data from OpenWeatherMap API and updates
the weather_grid table in the database. Uses the same grid cell structure
as the seed script (0.05 degree cells covering Mumbai).
"""

import asyncio
import datetime
from typing import Optional

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings, AsyncSessionLocal
from app.models.db_models import WeatherGrid


# Mumbai grid parameters (must match seed_synthetic_data.py)
MUMBAI_GRID = {
    "min_lat": 18.90,
    "max_lat": 19.50,
    "min_lon": 72.75,
    "max_lon": 73.20,
    "cell_size": 0.05,
}

# OpenWeatherMap condition code mapping
OWM_CONDITION_MAP = {
    "Thunderstorm": "thunderstorm",
    "Drizzle": "rain",
    "Rain": "rain",
    "Snow": "snow",
    "Mist": "mist",
    "Smoke": "mist",
    "Haze": "mist",
    "Dust": "mist",
    "Fog": "fog",
    "Sand": "mist",
    "Ash": "mist",
    "Squall": "heavy rain",
    "Tornado": "thunderstorm",
    "Clear": "clear",
    "Clouds": "cloudy",
}


def _classify_condition(owm_main: str, rain_1h: float) -> str:
    """Map OpenWeatherMap main condition + rain volume to our schema."""
    if rain_1h > 7.5:
        return "heavy rain"
    base = OWM_CONDITION_MAP.get(owm_main, "clear")
    return base


async def fetch_weather_for_point(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
    api_key: str,
) -> Optional[dict]:
    """Fetch current weather from OpenWeatherMap for a single coordinate."""
    try:
        resp = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "lat": lat,
                "lon": lon,
                "appid": api_key,
                "units": "metric",
            },
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            main = data.get("weather", [{}])[0].get("main", "Clear")
            rain_1h = data.get("rain", {}).get("1h", 0.0)
            return {
                "temperature": data.get("main", {}).get("temp"),
                "humidity": data.get("main", {}).get("humidity"),
                "visibility_km": round((data.get("visibility", 10000) or 10000) / 1000.0, 1),
                "precipitation_mm": round(rain_1h, 1),
                "wind_speed_kmh": round((data.get("wind", {}).get("speed", 0) or 0) * 3.6, 1),
                "weather_condition": _classify_condition(main, rain_1h),
            }
        else:
            print(f"[WeatherService] API returned {resp.status_code} for ({lat}, {lon})")
            return None
    except Exception as e:
        print(f"[WeatherService] Error fetching weather for ({lat}, {lon}): {e}")
        return None


async def refresh_weather_grid():
    """
    Refresh all weather grid cells from the OpenWeatherMap API.

    Strategy: Sample a sparse grid of representative points (every ~0.1 deg)
    and propagate each result to surrounding cells. This keeps API calls
    within the free-tier limit (~60/min) while covering the full Mumbai area.
    """
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        print("[WeatherService] No OPENWEATHER_API_KEY configured. Skipping refresh.")
        return

    print(f"[WeatherService] Starting weather grid refresh at {datetime.datetime.utcnow().isoformat()}...")

    grid = MUMBAI_GRID
    sample_step = 0.10  # Sample every ~11km (reduces API calls to ~54)

    weather_results = []

    # 1. Fetch all weather data from OpenWeatherMap API in-memory (no DB session is open during this rate-limited phase)
    async with httpx.AsyncClient() as client:
        lat = grid["min_lat"]
        while lat < grid["max_lat"]:
            lon = grid["min_lon"]
            while lon < grid["max_lon"]:
                sample_lat = lat + sample_step / 2
                sample_lon = lon + sample_step / 2

                weather = await fetch_weather_for_point(client, sample_lat, sample_lon, api_key)

                if weather:
                    bbox_wkt = (
                        f"POLYGON(({lon} {lat}, {lon + sample_step} {lat}, "
                        f"{lon + sample_step} {lat + sample_step}, {lon} {lat + sample_step}, "
                        f"{lon} {lat}))"
                    )
                    weather_results.append((weather, bbox_wkt))

                # Rate limit: OpenWeatherMap free tier allows 60 calls/min
                await asyncio.sleep(1.1)

                lon += sample_step
            lat += sample_step

    # 2. Open DB session and execute all updates inside a short-lived transaction
    if weather_results:
        async with AsyncSessionLocal() as db:
            updates_applied = 0
            from sqlalchemy import text

            stmt = text("""
                UPDATE weather_grid
                SET temperature = :temp,
                    humidity = :humidity,
                    visibility_km = :vis,
                    precipitation_mm = :precip,
                    wind_speed_kmh = :wind,
                    weather_condition = :cond,
                    recorded_at = :now
                WHERE ST_Intersects(
                    ST_Centroid(cell_geometry),
                    ST_GeomFromText(:bbox, 4326)
                )
            """)

            try:
                for weather, bbox_wkt in weather_results:
                    result = await db.execute(stmt, {
                        "temp": weather["temperature"],
                        "humidity": weather["humidity"],
                        "vis": weather["visibility_km"],
                        "precip": weather["precipitation_mm"],
                        "wind": weather["wind_speed_kmh"],
                        "cond": weather["weather_condition"],
                        "now": datetime.datetime.utcnow(),
                        "bbox": bbox_wkt,
                    })
                    updates_applied += result.rowcount or 0
                await db.commit()
                print(f"[WeatherService] Weather grid refresh complete. Updated {updates_applied} cells.")
            except Exception as e:
                await db.rollback()
                raise e
    else:
        print("[WeatherService] No weather data fetched, skipping database update.")
