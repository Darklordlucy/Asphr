import logging
import asyncio
import time
from typing import Optional, Tuple, Dict, Any
import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point

from app.config import settings
from app.models.db_models import PopularPlace

logger = logging.getLogger(__name__)

class GeocodingService:
    # Class-level variable to enforce global Nominatim rate limiting (1 request per second)
    _last_nominatim_call = 0.0
    _nominatim_lock = asyncio.Lock()

    def __init__(self):
        self.mapbox_token = settings.MAPBOX_TOKEN
        # In-memory caches rounded to 5 decimal places for reverse geocoding
        self.forward_cache: Dict[str, Tuple[float, float]] = {}
        self.reverse_cache: Dict[Tuple[float, float], Dict[str, Any]] = {}

    async def _wait_for_nominatim(self):
        """Enforces a strict 1-second delay between Nominatim calls globally."""
        async with self._nominatim_lock:
            now = time.time()
            elapsed = now - GeocodingService._last_nominatim_call
            if elapsed < 1.0:
                sleep_time = 1.0 - elapsed
                logger.info(f"Nominatim rate limit safeguard: sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
            GeocodingService._last_nominatim_call = time.time()

    async def forward_geocode(self, query: str, db: AsyncSession) -> Optional[Tuple[float, float]]:
        """
        Geocode a text address or place query to [longitude, latitude].
        Checks:
          1. In-memory cache
          2. Database popular_places table
          3. Mapbox Geocoding API
          4. Nominatim (OpenStreetMap) fallback if Mapbox limits are reached
        """
        query_norm = query.strip().lower()
        if not query_norm:
            return None

        # 1. Check in-memory cache
        if query_norm in self.forward_cache:
            logger.info(f"Forward geocode cache hit (in-memory): '{query}'")
            return self.forward_cache[query_norm]

        # 2. Check Database popular_places table
        try:
            stmt = select(PopularPlace).where(func.lower(PopularPlace.name) == query_norm).limit(1)
            result = await db.execute(stmt)
            db_place = result.scalar_one_or_none()
            if db_place:
                geom = to_shape(db_place.geometry)
                lon, lat = geom.x, geom.y
                self.forward_cache[query_norm] = (lon, lat)
                logger.info(f"Forward geocode cache hit (database popular_places): '{query}' -> [{lon}, {lat}]")
                return (lon, lat)
        except Exception as e:
            logger.warning(f"Database geocode cache lookup failed: {e}")

        # 3. Try Mapbox Geocoding API
        if self.mapbox_token:
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{httpx.URL(query_norm).raw_path.decode()}.json"
            params = {
                "access_token": self.mapbox_token,
                "limit": 1,
                "bbox": "72.75,18.90,73.20,19.50" # Restrict results to Mumbai area bounds
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=5.0)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("features"):
                        feature = data["features"][0]
                        lon, lat = feature["center"]
                        
                        # Cache in memory
                        self.forward_cache[query_norm] = (lon, lat)
                        
                        # Cache in database popular_places
                        await self._cache_to_db(query, lat, lon, db)
                        logger.info(f"Mapbox Forward Geocode success: '{query}' -> [{lon}, {lat}]")
                        return (lon, lat)
                    else:
                        logger.info(f"Mapbox Forward Geocode returned no features for: '{query}'")
                elif response.status_code == 429:
                    logger.warning("Mapbox rate limit reached. Falling back to Nominatim.")
                else:
                    logger.warning(f"Mapbox Forward Geocode failed with status {response.status_code}. Falling back to Nominatim.")
            except Exception as e:
                logger.error(f"Mapbox Forward Geocode API request error: {e}. Falling back to Nominatim.")

        # 4. Fallback to Nominatim (OpenStreetMap)
        logger.info(f"Using Nominatim fallback forward geocode for query: '{query}'")
        await self._wait_for_nominatim()
        
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "Asphr-Routing-Engine/1.0 (ualla@ualla.com)"}
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "viewbox": "72.75,18.90,73.20,19.50", # Limit/bias to Mumbai bounding box
            "bounded": 1
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data:
                    res = data[0]
                    lon, lat = float(res["lon"]), float(res["lat"])
                    
                    # Cache in memory
                    self.forward_cache[query_norm] = (lon, lat)
                    
                    # Cache in database popular_places
                    await self._cache_to_db(query, lat, lon, db)
                    logger.info(f"Nominatim Forward Geocode success: '{query}' -> [{lon}, {lat}]")
                    return (lon, lat)
                else:
                    logger.info(f"Nominatim Forward Geocode returned no results for: '{query}'")
            else:
                logger.error(f"Nominatim Forward Geocode failed with status: {response.status_code}")
        except Exception as e:
            logger.error(f"Nominatim Forward Geocode exception: {e}")

        return None

    async def reverse_geocode(self, lat: float, lon: float, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """
        Reverse geocode [longitude, latitude] coordinates to address and components.
        Checks:
          1. In-memory cache (coordinates rounded to 5 decimal places / ~1m accuracy)
          2. Mapbox Reverse Geocoding API
          3. Nominatim (OpenStreetMap) fallback if Mapbox limits are reached
        """
        # Round to 5 decimal places for robust caching (~1.1 meter resolution)
        lat_rounded = round(lat, 5)
        lon_rounded = round(lon, 5)
        cache_key = (lat_rounded, lon_rounded)

        # 1. Check in-memory cache
        if cache_key in self.reverse_cache:
            logger.info(f"Reverse geocode cache hit (in-memory): [{lat_rounded}, {lon_rounded}]")
            return self.reverse_cache[cache_key]

        # 2. Try Mapbox Reverse Geocoding API
        if self.mapbox_token:
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lon},{lat}.json"
            params = {
                "access_token": self.mapbox_token,
                "limit": 1
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=5.0)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("features"):
                        feature = data["features"][0]
                        place_name = feature["place_name"]
                        
                        # Extract context elements (city, state, country, etc.)
                        components = {}
                        for ctx in feature.get("context", []):
                            ctx_id = ctx.get("id", "")
                            if ctx_id.startswith("place"):
                                components["city"] = ctx.get("text", "")
                            elif ctx_id.startswith("region"):
                                components["state"] = ctx.get("text", "")
                            elif ctx_id.startswith("country"):
                                components["country"] = ctx.get("text", "")
                            elif ctx_id.startswith("postcode"):
                                components["postcode"] = ctx.get("text", "")
                        
                        result = {
                            "address": place_name,
                            "components": components
                        }
                        
                        # Cache in memory
                        self.reverse_cache[cache_key] = result
                        logger.info(f"Mapbox Reverse Geocode success: [{lat}, {lon}] -> '{place_name}'")
                        return result
                    else:
                        logger.info(f"Mapbox Reverse Geocode returned no features for: [{lat}, {lon}]")
                elif response.status_code == 429:
                    logger.warning("Mapbox reverse rate limit reached. Falling back to Nominatim.")
                else:
                    logger.warning(f"Mapbox Reverse Geocode failed with status {response.status_code}. Falling back to Nominatim.")
            except Exception as e:
                logger.error(f"Mapbox Reverse Geocode API request error: {e}. Falling back to Nominatim.")

        # 3. Fallback to Nominatim (OpenStreetMap)
        logger.info(f"Using Nominatim fallback reverse geocode for coordinates: [{lat}, {lon}]")
        await self._wait_for_nominatim()

        url = "https://nominatim.openstreetmap.org/reverse"
        headers = {"User-Agent": "Asphr-Routing-Engine/1.0 (ualla@ualla.com)"}
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json"
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data:
                    place_name = data.get("display_name", "")
                    addr = data.get("address", {})
                    components = {
                        "city": addr.get("city", addr.get("town", addr.get("suburb", ""))),
                        "state": addr.get("state", ""),
                        "country": addr.get("country", ""),
                        "postcode": addr.get("postcode", "")
                    }
                    
                    result = {
                        "address": place_name,
                        "components": components
                    }
                    
                    # Cache in memory
                    self.reverse_cache[cache_key] = result
                    logger.info(f"Nominatim Reverse Geocode success: [{lat}, {lon}] -> '{place_name}'")
                    return result
                else:
                    logger.info(f"Nominatim Reverse Geocode returned no results for: [{lat}, {lon}]")
            else:
                logger.error(f"Nominatim Reverse Geocode failed with status: {response.status_code}")
        except Exception as e:
            logger.error(f"Nominatim Reverse Geocode exception: {e}")

        return None

    async def _cache_to_db(self, name: str, lat: float, lon: float, db: AsyncSession):
        """Asynchronously cache the geocoding results to popular_places table."""
        try:
            # Check if it already exists to avoid unique constraint violations or duplicates
            stmt = select(PopularPlace).where(func.lower(PopularPlace.name) == name.strip().lower()).limit(1)
            res = await db.execute(stmt)
            if res.scalar_one_or_none():
                return

            new_place = PopularPlace(
                name=name,
                category="cached_geocode",
                geometry=from_shape(Point(lon, lat), srid=4326),
                popularity_score=0.0,
                city="Mumbai"
            )
            db.add(new_place)
            await db.commit()
            logger.info(f"Cached forward geocode to popular_places DB table: '{name}'")
        except Exception as e:
            await db.rollback()
            logger.warning(f"Failed to cache geocode to database popular_places: {e}")
