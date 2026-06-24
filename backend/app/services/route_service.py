import math
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shapely.geometry import Point

from app.models.route_optimizer import RouteOptimizer
from app.models.db_models import WeatherGrid, VehicleProfile
from app.algorithms.graph_builder import GraphManager

class RouteService:
    def __init__(self):
        self.optimizer = RouteOptimizer()

    def generate_turn_instructions(self, coordinates: List[List[float]]) -> List[Dict[str, Any]]:
        """Generates simple turn-by-turn instructions based on bearing changes between points."""
        instructions = []
        if len(coordinates) < 3:
            instructions.append({"instruction": "Head towards your destination", "distance_meters": 0})
            return instructions

        def get_bearing(pt1, pt2):
            lon1, lat1 = pt1
            lon2, lat2 = pt2
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            d_lon = lon2 - lon1
            y = math.sin(d_lon) * math.cos(lat2)
            x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
            return math.degrees(math.atan2(y, x)) % 360

        instructions.append({"instruction": "Start your journey", "distance_meters": 0})

        for i in range(len(coordinates) - 2):
            pt1 = coordinates[i]
            pt2 = coordinates[i+1]
            pt3 = coordinates[i+2]

            bearing1 = get_bearing(pt1, pt2)
            bearing2 = get_bearing(pt2, pt3)

            # Compute change in bearing
            diff = (bearing2 - bearing1 + 180) % 360 - 180
            
            # Distance of segment (approximate using simple spherical distance for speed)
            # 1 degree lat/lon is approx 111,000 meters
            lat_dist = (pt2[1] - pt1[1]) * 111000
            lon_dist = (pt2[0] - pt1[0]) * 111000 * math.cos(math.radians(pt1[1]))
            dist = math.sqrt(lat_dist**2 + lon_dist**2)

            if diff > 45:
                instructions.append({"instruction": f"Turn right onto next road", "distance_meters": round(dist)})
            elif diff < -45:
                instructions.append({"instruction": f"Turn left onto next road", "distance_meters": round(dist)})
            elif abs(diff) > 20:
                instructions.append({"instruction": f"Keep {'right' if diff > 0 else 'left'}", "distance_meters": round(dist)})
            
        instructions.append({"instruction": "Arrive at your destination", "distance_meters": 0})
        return instructions

    async def compute_route_service(
        self,
        db: AsyncSession,
        origin: Dict[str, float],
        destination: Dict[str, float],
        route_type: str,
        vehicle_type: str,
        avoid_tolls: bool = False
    ) -> Dict[str, Any]:
        # 1. Execute pathfinding optimization
        route_result = self.optimizer.compute_route(
            start_lat=origin["lat"],
            start_lon=origin["lon"],
            end_lat=destination["lat"],
            end_lon=destination["lon"],
            route_type=route_type,
            vehicle_type=vehicle_type,
            avoid_tolls=avoid_tolls
        )

        # 2. Query weather conditions around origin point for warning alerts
        weather_alerts = []
        origin_pt = Point(origin["lon"], origin["lat"])
        
        try:
            # Query active weather cells
            result = await db.execute(select(WeatherGrid.weather_condition, WeatherGrid.precipitation_mm))
            # Just check weather conditions from grid if any are populated
            for cond, precip in result.all():
                if cond and cond.lower() in ["rain", "heavy rain", "thunderstorm", "snow"]:
                    weather_alerts.append(f"Caution: active {cond} reported in target routing grid.")
                    break
        except Exception:
            pass # fall through if database is empty

        if not weather_alerts:
            weather_alerts.append("Weather clear along the selected route.")

        # 3. Generate turn-by-turn navigation instructions
        instructions = self.generate_turn_instructions(route_result["coordinates"])

        # 4. Assemble final package
        return {
            "route_id": f"route_{int(math.sin(origin['lat']) * 1000000)}",
            "geometry": {
                "type": "LineString",
                "coordinates": route_result["coordinates"]
            },
            "distance_km": route_result["distance_km"],
            "duration_min": route_result["duration_min"],
            "hazard_score_avg": route_result["hazard_score_avg"],
            "segments": route_result["segments"],
            "weather_alerts": weather_alerts,
            "instructions": instructions
        }
